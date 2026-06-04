"use client";

import { Skeleton } from "@mantine/core";
import classes from "./RecordRowList.module.css";

export default function RecordRowSkeleton({ rows = 8 }: { rows?: number }) {
  const template = "minmax(140px, 2.2fr) repeat(4, minmax(72px, 1fr)) 32px";

  return (
    <div className={classes.panel}>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={`row-skeleton-${index}`}
          className={classes.row}
          style={{ gridTemplateColumns: template, gap: 10 }}
        >
          <Skeleton height={12} radius="sm" width="75%" />
          <Skeleton height={12} radius="sm" />
          <Skeleton height={12} radius="sm" />
          <Skeleton height={12} radius="sm" />
          <Skeleton height={12} radius="sm" />
          <Skeleton height={12} width={16} radius="sm" />
        </div>
      ))}
    </div>
  );
}
