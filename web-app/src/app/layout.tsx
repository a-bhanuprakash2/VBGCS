import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gesture Controller v4 - Web Edition",
  description: "Web-based gesture control and smartboard built with MediaPipe and Next.js",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
