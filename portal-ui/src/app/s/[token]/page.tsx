"use client";

import {
  Alert,
  Badge,
  Button,
  Container,
  FileButton,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { IconCheck, IconPaperclip, IconSend } from "@tabler/icons-react";
import { useCallback, useRef, useState } from "react";
import { useT } from "@orbiteus/i18n";

import { extractApiError } from "@/lib/api";
import {
  usePortalAttachment,
  usePortalComment,
  useShareResourceView,
} from "@/lib/queries/share";
import { useRealtimeShareResource } from "@/lib/realtime";

export default function ShareLinkPage({ params }: { params: { token: string } }) {
  return <ShareLinkPageInner params={params} />;
}

function ShareLinkPageInner({ params }: { params: { token: string } }) {
  const t = useT();
  const viewQuery = useShareResourceView(params.token);
  const view = viewQuery.data ?? null;
  const error = viewQuery.isError
    ? extractApiError(viewQuery.error, t("portal.share.invalidLink"))
    : null;
  const loading = viewQuery.isLoading && !viewQuery.data;

  const [liveAt, setLiveAt] = useState<number | null>(null);

  const onRealtime = useCallback(() => {
    setLiveAt(Date.now());
    void viewQuery.refetch();
  }, [viewQuery]);

  useRealtimeShareResource(
    {
      shareToken: params.token,
      tenantId: view?.tenant_id,
      model: view?.resource_model,
      recordId: view?.resource_id,
    },
    onRealtime,
  );

  const canComment = view?.available_mutations.includes("portal.comment") ?? false;
  const canAttach = view?.available_mutations.includes("portal.attachment") ?? false;

  return (
    <Container size="md" py="xl">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={2}>{t("portal.share.title")}</Title>
          {liveAt ? (
            <Badge color="green" variant="light">
              {t("portal.share.liveUpdate", { time: new Date(liveAt).toLocaleTimeString() })}
            </Badge>
          ) : null}
        </Group>
        {error ? <Alert color="red" title={t("portal.share.cannotOpen")}>{error}</Alert> : null}
        {loading ? <Loader /> : null}
        {view ? (
          <>
            <Paper withBorder p="md">
              <Group justify="space-between" mb="xs">
                <Text fw={600}>
                  {view.resource_model} / {view.resource_id}
                </Text>
                <Badge variant="light" color="gray">
                  {view.view_mode}
                </Badge>
              </Group>
              <Text size="sm" c="dimmed" mt="xs">
                {t("portal.share.permissions")}: {view.permissions.join(", ")}
              </Text>
              <pre style={{ marginTop: 12, whiteSpace: "pre-wrap" }}>
                {JSON.stringify(view.payload, null, 2)}
              </pre>
            </Paper>
            {canComment ? <CommentSurface token={params.token} /> : null}
            {canAttach ? <AttachmentSurface token={params.token} /> : null}
          </>
        ) : null}
      </Stack>
    </Container>
  );
}

function CommentSurface({ token }: { token: string }) {
  const t = useT();
  const commentMutation = usePortalComment(token);
  const [body, setBody] = useState("");
  const [feedback, setFeedback] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  async function handleSubmit() {
    if (!body.trim()) return;
    setFeedback(null);
    try {
      await commentMutation.mutateAsync(body.trim());
      setBody("");
      setFeedback({ kind: "ok", msg: t("portal.share.commentRecorded") });
    } catch (err) {
      setFeedback({ kind: "err", msg: extractApiError(err, t("portal.share.commentFailed")) });
    }
  }

  return (
    <Paper withBorder p="md">
      <Stack gap="sm">
        <Title order={4}>{t("portal.share.addComment")}</Title>
        <Textarea
          placeholder={t("portal.share.commentPlaceholder")}
          value={body}
          onChange={(e) => setBody(e.currentTarget.value)}
          autosize
          minRows={3}
          maxRows={8}
        />
        <Group justify="space-between" align="center">
          {feedback ? (
            <Text size="sm" c={feedback.kind === "ok" ? "green" : "red"}>
              {feedback.msg}
            </Text>
          ) : <span />}
          <Button
            leftSection={<IconSend size={16} />}
            loading={commentMutation.isPending}
            onClick={handleSubmit}
            disabled={!body.trim()}
          >
            {t("portal.share.send")}
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}

function AttachmentSurface({ token }: { token: string }) {
  const t = useT();
  const attachmentMutation = usePortalAttachment(token);
  const [file, setFile] = useState<File | null>(null);
  const resetRef = useRef<() => void>(null);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  async function handleSubmit() {
    if (!file) return;
    setFeedback(null);
    try {
      await attachmentMutation.mutateAsync(file);
      setFile(null);
      resetRef.current?.();
      setFeedback({ kind: "ok", msg: t("portal.share.attachmentUploaded") });
    } catch (err) {
      setFeedback({ kind: "err", msg: extractApiError(err, t("portal.share.attachmentFailed")) });
    }
  }

  return (
    <Paper withBorder p="md">
      <Stack gap="sm">
        <Title order={4}>{t("portal.share.addAttachment")}</Title>
        <Group>
          <FileButton onChange={setFile} resetRef={resetRef}>
            {(props) => (
              <Button {...props} variant="default" leftSection={<IconPaperclip size={16} />}>
                {file ? t("portal.share.changeFile") : t("portal.share.pickFile")}
              </Button>
            )}
          </FileButton>
          {file ? <Text size="sm">{file.name} ({Math.round(file.size / 1024)} KB)</Text> : null}
        </Group>
        <Group justify="space-between" align="center">
          {feedback ? (
            <Text size="sm" c={feedback.kind === "ok" ? "green" : "red"}>
              {feedback.kind === "ok" ? <IconCheck size={14} style={{ verticalAlign: -2 }} /> : null}
              {" "}{feedback.msg}
            </Text>
          ) : <span />}
          <Button
            onClick={handleSubmit}
            loading={attachmentMutation.isPending}
            disabled={!file}
          >
            {t("portal.share.upload")}
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}
