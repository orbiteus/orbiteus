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

interface Params { module: string; model: string; }

const FALLBACK = (t: (k: string) => string): FieldDef[] => [
  { key: "name", label: t("field.name"), type: "text", required: true },
];

export default function DynamicCreatePage({ params }: { params: Promise<Params> }) {
  const { module: mod, model } = use(params);
  const resource = `${mod}/${model}`;
  const t = useT();
  const uiConfig = useUiConfig();
  const { model: cfg, isLoading, isFetched } = useUiConfigModel(mod, model);
  const title = useTranslatedModelTitle(cfg, model);

  if (isFetched && !isKnownModel(uiConfig.data, mod, model)) {
    return <UnknownModelNotice module={mod} model={model} />;
  }
  const form = useTranslatedFormStructure(cfg);

  const resolved = useMemo((): { fields: FieldDef[]; panels?: FormPanels } | null => {
    if (!isFetched && isLoading) return null;
    if (form && cfg && cfg.fields.length > 0) return form;
    return { fields: FALLBACK(t) };
  }, [form, cfg, isLoading, isFetched, t]);

  if (!resolved) {
    return <Center h={200}><Loader color="gray" size="sm" /></Center>;
  }

  return (
    <ResourceForm
      title={t("form.createTitle", { title })}
      resource={resource}
      fields={resolved.fields}
      panels={resolved.panels}
      backHref={`/${mod}/${model}`}
    />
  );
}
