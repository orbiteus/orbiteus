"use client";
import { use, useMemo } from "react";
import ResourceForm, { type FieldDef } from "@/components/ResourceForm";
import { Loader, Center } from "@mantine/core";
import UnknownModelNotice from "@/components/UnknownModelNotice";
import { isKnownModel } from "@/lib/knownModels";
import { useUiConfig, useUiConfigModel } from "@/lib/queries/uiConfig";
import { useTranslatedFormStructure, useTranslatedModelTitle } from "@/lib/translatedModel";
import { useT } from "@orbiteus/i18n";
import type { FormPanels } from "@/lib/modelConfig";

interface Params { module: string; model: string; id: string; }

const FALLBACK: FieldDef[] = [{ key: "name", label: "Name", type: "text", required: true }];

export default function DynamicEditPage({ params }: { params: Promise<Params> }) {
  const { module: mod, model, id } = use(params);
  const resource = `${mod}/${model}`;
  const t = useT();
  const uiConfig = useUiConfig();
  const { model: cfg, isLoading, isFetched } = useUiConfigModel(mod, model);
  const title = useTranslatedModelTitle(cfg, model);
  const form = useTranslatedFormStructure(cfg);

  if (isFetched && !isKnownModel(uiConfig.data, mod, model)) {
    return <UnknownModelNotice module={mod} model={model} />;
  }

  const resolved = useMemo((): { fields: FieldDef[]; panels?: FormPanels } | null => {
    if (!isFetched && isLoading) return null;
    if (form && cfg && cfg.fields.length > 0) return form;
    return { fields: FALLBACK };
  }, [form, cfg, isLoading, isFetched]);

  if (!resolved) {
    return <Center h={200}><Loader color="gray" size="sm" /></Center>;
  }

  return (
    <ResourceForm
      title={t("form.editTitle", { title })}
      resource={resource}
      recordId={id}
      fields={resolved.fields}
      panels={resolved.panels}
      backHref={`/${mod}/${model}`}
      aiScope={`module:${mod}` as const}
    />
  );
}
