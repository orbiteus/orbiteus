"""XML view loader for Orbiteus modules.

Loads view definitions from XML files, applies XPath inheritance, and seeds
them into the ir_ui_views table.

XML format (single file can contain multiple views):
    <views>
      <view name="crm.customer.list" model="crm.customer" type="list">
        <list>
          <field name="name"/>
          <field name="email"/>
          <field name="status"/>
        </list>
      </view>

      <view name="crm.customer.form" model="crm.customer" type="form">
        <form>
          <group>
            <field name="name" required="1"/>
            <field name="email"/>
          </group>
        </form>
      </view>
    </views>

Inheritance (add fields to existing views without touching the original file):
    <views>
      <view inherit="crm.customer.form" priority="100">
        <xpath expr="//field[@name='email']" position="after">
          <field name="phone"/>
        </xpath>
      </view>
    </views>

Supported XPath positions: after, before, inside, replace, attributes
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from lxml import etree
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ViewDefinition(BaseModel):
    """Parsed view definition from XML file."""
    name: str
    model: str
    type: str = "form"
    arch: str = "<view/>"
    inherit_name: str | None = None   # name of parent view (before DB id resolution)
    priority: int = 16
    module: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_xml_views(xml_path: Path, module_name: str) -> list[ViewDefinition]:
    """Parse an XML view file and return list of ViewDefinition objects.

    A single XML file can contain multiple <view> elements wrapped in <views>.
    """
    if not xml_path.exists():
        raise FileNotFoundError(f"View file not found: {xml_path}")

    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML in {xml_path}: {e}") from e

    root = tree.getroot()
    views: list[ViewDefinition] = []

    # Support both <views>...</views> wrapper and bare <view> root
    view_elements = root.findall("view") if root.tag == "views" else [root]

    for el in view_elements:
        view = _parse_view_element(el, module_name)
        if view:
            views.append(view)

    logger.debug("Loaded %d views from %s", len(views), xml_path)
    return views


def resolve_arch(base_arch: str, inherit_archs: list[str]) -> str:
    """Apply XPath inheritance operations to a base arch XML string.

    Each inherit_arch is an XML string containing <xpath> elements.
    Returns the final resolved arch as a string.
    """
    if not inherit_archs:
        return base_arch

    try:
        doc = etree.fromstring(base_arch.encode())
    except etree.XMLSyntaxError as e:
        logger.error("Could not parse base arch: %s", e)
        return base_arch

    for inherit_arch in inherit_archs:
        try:
            inherit_doc = etree.fromstring(inherit_arch.encode())
        except etree.XMLSyntaxError as e:
            logger.warning("Could not parse inherit arch: %s", e)
            continue

        xpaths = inherit_doc.findall("xpath")
        if not xpaths:
            # The inherit arch itself might be a single xpath element
            if inherit_doc.tag == "xpath":
                xpaths = [inherit_doc]

        for xpath_el in xpaths:
            _apply_xpath(doc, xpath_el)

    return etree.tostring(doc, encoding="unicode", pretty_print=True)


async def seed_views_to_db(
    views: list[ViewDefinition],
    session: Any,
    ctx: Any,
) -> None:
    """Upsert view definitions into ir_ui_views table.

    Idempotent — updates existing views by name, inserts new ones.
    inherit_name is resolved to inherit_id via DB lookup.
    """
    from modules.base.controller.repositories import IrUiViewRepository

    repo = IrUiViewRepository(session, ctx)

    for view in views:
        # Resolve inherit_id if this is an inherited view
        inherit_id = None
        if view.inherit_name:
            parents, _ = await repo.search(
                domain=[("name", "=", view.inherit_name)], limit=1,
            )
            if parents:
                inherit_id = parents[0].id
            else:
                logger.warning(
                    "View '%s' inherits from '%s' which doesn't exist yet — skipping inherit_id",
                    view.name, view.inherit_name,
                )

        data = {
            "name":       view.name,
            "model":      view.model,
            "type":       view.type,
            "arch":       view.arch,
            "inherit_id": inherit_id,
            "priority":   view.priority,
            "active":     True,
            "module":     view.module,
        }

        existing, _ = await repo.search(domain=[("name", "=", view.name)], limit=1)
        if existing:
            await repo.update(existing[0].id, data)
        else:
            await repo.create(data)

    logger.info("Seeded %d views to DB from module '%s'", len(views), views[0].module if views else "?")


def get_resolved_arch_for_model(model: str, view_type: str, views_cache: dict[str, ViewDefinition]) -> str | None:
    """Resolve final arch for a model+type from in-memory cache.

    Applies inheritance chain. Returns resolved XML string or None if not found.
    Used before DB is available (during bootstrap).
    """
    # Find base view (no inherit_name, lowest priority)
    base = None
    for v in views_cache.values():
        if v.model == model and v.type == view_type and v.inherit_name is None:
            if base is None or v.priority < base.priority:
                base = v

    if base is None:
        return None

    # Collect inherit views in priority order
    inherits = sorted(
        [v for v in views_cache.values() if v.inherit_name == base.name],
        key=lambda v: v.priority,
    )

    return resolve_arch(base.arch, [i.arch for i in inherits])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_view_element(el: etree._Element, module_name: str) -> ViewDefinition | None:
    """Parse a single <view> element into a ViewDefinition."""
    inherit_name = el.get("inherit")

    if inherit_name:
        # Inherited view: no name/model/type required on the element itself
        name = el.get("name") or f"{inherit_name}.inherit.{module_name}"
        # model and type are inherited — use empty strings, will be resolved from parent
        model = el.get("model", "")
        view_type = el.get("type", "form")
        priority = int(el.get("priority", "100"))
    else:
        name = el.get("name")
        model = el.get("model")
        view_type = el.get("type", "form")
        priority = int(el.get("priority", "16"))

        if not name or not model:
            logger.warning("Skipping <view> element missing name or model: %s", etree.tostring(el))
            return None

    # Serialize the inner content as the arch
    # For non-inherited views: serialize the first child element
    # For inherited views: serialize all xpath elements
    arch = _extract_arch(el)

    return ViewDefinition(
        name=name,
        model=model,
        type=view_type,
        arch=arch,
        inherit_name=inherit_name,
        priority=priority,
        module=module_name,
    )


def _extract_arch(el: etree._Element) -> str:
    """Extract the arch (inner XML) from a view element."""
    children = list(el)
    if not children:
        return "<view/>"

    if len(children) == 1:
        return etree.tostring(children[0], encoding="unicode", pretty_print=True).strip()

    # Multiple children — wrap in a container
    wrapper = etree.Element("arch")
    for child in children:
        wrapper.append(child)
    return etree.tostring(wrapper, encoding="unicode", pretty_print=True).strip()


def _apply_xpath(doc: etree._Element, xpath_el: etree._Element) -> None:
    """Apply a single <xpath> operation to the document tree."""
    expr = xpath_el.get("expr")
    position = xpath_el.get("position", "inside")

    if not expr:
        logger.warning("XPath element missing 'expr' attribute, skipping")
        return

    try:
        targets = doc.xpath(expr)
    except etree.XPathEvalError as e:
        logger.warning("Invalid XPath expression %r: %s", expr, e)
        return

    if not targets:
        logger.warning("XPath %r matched no elements in arch", expr)
        return

    target = targets[0]
    new_elements = list(xpath_el)

    if position == "inside":
        for child in new_elements:
            target.append(child)

    elif position == "after":
        parent = target.getparent()
        if parent is None:
            logger.warning("Cannot insert 'after' root element")
            return
        idx = list(parent).index(target)
        for i, child in enumerate(new_elements):
            parent.insert(idx + 1 + i, child)

    elif position == "before":
        parent = target.getparent()
        if parent is None:
            logger.warning("Cannot insert 'before' root element")
            return
        idx = list(parent).index(target)
        for i, child in enumerate(new_elements):
            parent.insert(idx + i, child)

    elif position == "replace":
        parent = target.getparent()
        if parent is None:
            logger.warning("Cannot replace root element")
            return
        idx = list(parent).index(target)
        parent.remove(target)
        for i, child in enumerate(new_elements):
            parent.insert(idx + i, child)

    elif position == "attributes":
        # xpath_el children are <attribute name="...">value</attribute>
        for attr_el in xpath_el.findall("attribute"):
            attr_name = attr_el.get("name")
            if attr_name:
                if attr_el.text:
                    target.set(attr_name, attr_el.text)
                elif attr_name in target.attrib:
                    del target.attrib[attr_name]

    else:
        logger.warning("Unknown XPath position: %r", position)
