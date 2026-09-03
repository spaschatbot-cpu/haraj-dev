/**
 * إطار الوثيقة — T1003 وT1006.
 *
 * `lang="ar"` and `dir="rtl"` are set here, on the document, and not on a
 * wrapper somewhere inside it. Everything downstream — Tailwind's logical
 * properties, the browser's own text selection and caret behaviour, a screen
 * reader's pronunciation — reads the direction off `<html>`, so setting it once
 * here is what lets every layout below be written without a single
 * `direction`-aware rule of its own. RTL retrofitted later means rewriting each
 * of those layouts, which is why T1003 says «من أول commit».
 *
 * The font is self-hosted by `next/font`: it is downloaded at build time and
 * served from this origin, so a customer's browser makes no request to a third
 * party to render an Arabic page, and the page does not reflow when a
 * third-party font arrives late.
 */

import type { Metadata, Viewport } from "next";
import { Cairo } from "next/font/google";

import { EnvironmentBanner } from "@/features/shell/EnvironmentBanner";
import { environmentName } from "@/lib/environment";

import "./globals.css";

const cairo = Cairo({
  subsets: ["arabic", "latin"],
  variable: "--font-cairo",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "حراج", template: "%s — حراج" },
  description: "مزادات المركبات — تصفّح، وزايد، وتابع محفظتك.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl" className={cairo.variable}>
      <body className="min-h-screen antialiased">
        <EnvironmentBanner name={environmentName()} />
        {children}
      </body>
    </html>
  );
}
