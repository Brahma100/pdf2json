from invoice_ocr.validation.normalize import to_decimal
from invoice_ocr.validation.summary_labels import SUMMARY_LABELS
from invoice_ocr.table.geometry import center_x, center_y

def extract_summary(blocks, x_gap=300, y_tol=20):
    summary = {}

    for label_key, keywords in SUMMARY_LABELS.items():
        label_blocks = [
            b for b in blocks
            if any(k in b["text"].lower() for k in keywords)
        ]

        for label in label_blocks:
            ly = center_y(label["bbox"])
            lx = center_x(label["bbox"])

            # find value block to the RIGHT
            candidates = []
            for b in blocks:
                by = center_y(b["bbox"])
                bx = center_x(b["bbox"])

                if abs(by - ly) <= y_tol and bx > lx:
                    val = to_decimal(b["text"])
                    if val is not None:
                        candidates.append((bx, val))

            if candidates:
                # nearest value to the label
                candidates.sort(key=lambda x: x[0])
                summary[label_key] = candidates[0][1]

    return summary
