import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "REEL — Keep the good stuff",
  description: "Your download desk for YouTube and TikTok. Save video as MP4 or audio as MP3, straight to your device.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
