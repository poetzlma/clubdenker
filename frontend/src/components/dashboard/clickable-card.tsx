import { type KeyboardEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

interface ClickableCardProps {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  className?: string;
  disabled?: boolean;
}

export function ClickableCard({
  children,
  onClick,
  href,
  className,
  disabled = false,
}: ClickableCardProps) {
  const navigate = useNavigate();

  const isInteractive = !disabled && (!!href || !!onClick);

  function handleClick() {
    if (!isInteractive) return;
    if (href) {
      navigate(href);
    } else if (onClick) {
      onClick();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (!isInteractive) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  }

  return (
    <div
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
    </div>
  );
}
