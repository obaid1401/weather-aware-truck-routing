/** Hides content visually while keeping it available to screen readers. Pixel values are
 * strings because MUI's `sx` reads numbers up to 1 as percentages and others as spacing. */
export const visuallyHidden = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0 0 0 0)',
  whiteSpace: 'nowrap',
  border: 0,
} as const
