import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  confirmDisabled?: boolean;
  confirmPending?: boolean;
}

// Reemplaza los cuadros de confirmación que antes vivían dentro de una
// celda de tabla angosta, donde el contenido se superponía con los
// botones. Un modal centrado no tiene ese límite de espacio.
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  children,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  onConfirm,
  confirmDisabled = false,
  confirmPending = false,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <Dialog.Title className="dialog-title">{title}</Dialog.Title>
          {children && <div className="dialog-body">{children}</div>}
          <div className="dialog-actions">
            <Dialog.Close asChild>
              <button type="button" className="icon-btn" style={{ width: "auto", padding: "0.5rem 1rem" }}>
                {cancelLabel}
              </button>
            </Dialog.Close>
            <button
              type="button"
              className="icon-btn danger"
              style={{ width: "auto", padding: "0.5rem 1rem" }}
              onClick={onConfirm}
              disabled={confirmDisabled || confirmPending}
            >
              {confirmPending ? "Un momento..." : confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
