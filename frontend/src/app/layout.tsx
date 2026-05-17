import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SoundSight",
  description:
    "A local SoundSight app for demo clips and chunked live microphone alerts.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
