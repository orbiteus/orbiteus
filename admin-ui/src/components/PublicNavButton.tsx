"use client";

import type { MouseEventHandler, ReactNode } from "react";
import { Button, type ButtonProps } from "@mantine/core";
import { hardNavigate } from "@/lib/hardNavigate";

type PublicNavButtonProps = Omit<ButtonProps, "href" | "onClick" | "component"> & {
  href: string;
  children?: ReactNode;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
};

export function PublicNavButton({ href, onClick, children, ...props }: PublicNavButtonProps) {
  return (
    <Button
      component="a"
      href={href}
      onClick={(e) => {
        e.preventDefault();
        onClick?.(e);
        hardNavigate(href);
      }}
      {...props}
    >
      {children}
    </Button>
  );
}
