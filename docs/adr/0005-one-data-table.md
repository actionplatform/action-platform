# 0005 — One `DataTable`

**Status**: accepted · 2026-09-18 · [#235](https://github.com/actionplatform/action-platform/issues/235)

## Context

Four lists, four tables, four mobile layouts, four empty states; rows of different heights; menus clipped by overflow.

## Decision

`components/ui/data-table.tsx` fixes every dimension — toolbar 56, column header 40, rows 52, footer 56, 16px padding, 10px radius — and always renders ten row slots, the empty ones with separators only. Cells stay on one line with an ellipsis. Columns take a percentage width and hide progressively under `lg`; under `md` each row becomes a card built from the same columns — the first as the title, the rest as label/value pairs, the actions on the right — so phones scroll down, never sideways. Pages configure only columns and data. Menus render through a portal.

## Consequences

The four tables start and end at the same pixel. Expandable rows gave way to a details dialog. New lists cost a column array.
