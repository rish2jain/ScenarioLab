import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import { ClientLayout } from "@/components/ClientLayout";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  title: "MiroFish - AI War-Gaming Platform",
  description: "Strategic war-gaming platform for consultants",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${outfit.variable} font-sans antialiased bg-background text-foreground min-h-screen selection:bg-accent/30 selection:text-white`}
        suppressHydrationWarning
      >
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
