import { type KeyboardEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

interface ClickableRowProps {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  className?: string;
}

export function ClickableRow({
  children,
  onClick,
  href,
  className,
}: ClickableRowProps) {
  const navigate = useNavigate();

  const isInteractive = !!href || !!onClick;

  function handleClick() {
    if (!isInteractive) return;
    if (href) {
      navigate(href);
    } else if (onClick) {
      onClick();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTableRowElement>) {
    if (!isInteractive) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  }

  return (
    <tr
      className={cn(
        isInteractive &&
          "cursor-pointer transition-colors hover:bg-muted",
        className
      )}
      onClick={isInteractive ? handleClick : undefined}
      onKeyDown={isInteractive ? handleKeyDown : undefined}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
    >
      {children}
    </tr>
  );
}
