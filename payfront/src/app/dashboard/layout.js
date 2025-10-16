export const metadata = {
  title: {
    default: "Dashboard — Paytrack",
    template: "%s — Paytrack",
  },
  description: "Manage your tenant: wallet, transactions, callbacks, payouts and API keys.",
  robots: { index: false, follow: false },
};

export default function DashboardLayout({ children }) {
  return children;
}


