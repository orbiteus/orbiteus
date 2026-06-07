"use client";

import type { MouseEventHandler, ReactNode } from "react";
import { Anchor, type AnchorProps } from "@mantine/core";
import { hardNavigate } from "@/lib/hardNavigate";

type PublicNavLinkProps = Omit<AnchorProps, "href" | "onClick"> & {
  href: string;
  children?: ReactNode;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
};

export function PublicNavLink({ href, onClick, children, ...props }: PublicNavLinkProps) {
  return (
    <Anchor
      href={href}
      onClick={(e) => {
        e.preventDefault();
        onClick?.(e);
        hardNavigate(href);
      }}
      {...props}
    >
      {children}
    </Anchor>
  );
}
