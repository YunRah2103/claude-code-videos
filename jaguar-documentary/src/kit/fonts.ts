import {staticFile} from 'remotion';
const faces: [string, string, string, string][] = [
  ['Cormorant Garamond', '500', 'normal', 'cormorant-garamond-latin-500-normal.woff2'],
  ['Cormorant Garamond', '600', 'normal', 'cormorant-garamond-latin-600-normal.woff2'],
  ['Cormorant Garamond', '500', 'italic', 'cormorant-garamond-latin-500-italic.woff2'],
  ['Cormorant Garamond', '700', 'normal', 'cormorant-garamond-latin-700-normal.woff2'],
  ['Inter', '400', 'normal', 'inter-latin-400-normal.woff2'],
  ['Inter', '500', 'normal', 'inter-latin-500-normal.woff2'],
  ['Inter', '600', 'normal', 'inter-latin-600-normal.woff2'],
  ['Inter', '700', 'normal', 'inter-latin-700-normal.woff2'],
];
export const fontCss = faces
  .map(([f, w, s, file]) => `@font-face{font-family:"${f}";font-weight:${w};font-style:${s};src:url(${staticFile('fonts/' + file)}) format("woff2");}`)
  .join('\n');
