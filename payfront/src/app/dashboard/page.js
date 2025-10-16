"use client";

import { useEffect, useState } from "react";
import { Bell, Search } from "lucide-react";
import Tabs from "../../components/Tabs.jsx";
import { apiFetch } from "../../lib/api";
import styles from "./styles.module.css";

const fmtKES = (n) => `KES ${Number(n ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ callback_url: "", auto_payout: false, payment_method: { mpesa_number: "", paybill_number: "", account_number: "" } });
  const [confirmAutoPayoutOpen, setConfirmAutoPayoutOpen] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await apiFetch(`/tenants/dashboard/configs`, { method: "GET" });
        if (mounted) setData(res);
      } catch (e) {
        if (mounted) setError(e.message || "Failed to load dashboard");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  // hydrate form from loaded config
  useEffect(() => {
    if (!data?.config) return;
    const pm = data.config.payment_method || {};
    setForm({
      callback_url: data.config.callback_url || "",
      auto_payout: Boolean(data.config.auto_payout),
      payment_method: {
        mpesa_number: pm.mpesa_number || "",
        paybill_number: pm.paybill_number || "",
        account_number: pm.account_number || "",
      },
    });
  }, [data]);

  function hasPayoutMethodValue() {
    return Boolean(
      form.payment_method?.mpesa_number ||
      form.payment_method?.paybill_number ||
      form.payment_method?.account_number
    );
  }

  async function performSave() {
    try {
      setSaving(true);
      const hasPayoutMethod = hasPayoutMethodValue();
      const payload = {
        callback_url: form.callback_url || null,
        payment_method: {
          mpesa_number: form.payment_method.mpesa_number || null,
          paybill_number: form.payment_method.paybill_number || null,
          account_number: form.payment_method.account_number || null,
        },
        auto_payout: hasPayoutMethod ? Boolean(form.auto_payout) : false,
      };
      const updated = await apiFetch(`/tenants/dashboard/configs`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setData((d) => ({ ...(d || {}), config: updated.config || payload }));
      setEditing(false);
    } catch (e) {
      setError(e.message || "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  }

  async function onSaveConfig() {
    const enablingAutoPayout = Boolean(form.auto_payout) && !Boolean(data?.config?.auto_payout);
    if (enablingAutoPayout && hasPayoutMethodValue()) {
      setConfirmAutoPayoutOpen(true);
      return;
    }
    await performSave();
  }

  return (
    <div className={styles.shell}>
      <Tabs
        activeHref="/dashboard"
        items={[
          { label: "Home", href: "/dashboard" },
          { label: "Wallet", href: "/dashboard/wallet" },
          { label: "API Keys", href: "/dashboard/api-keys" },
        ]}
        brand="Paytrack"
      />

      <main className={styles.main}>
        <section className={styles.card}>
          <div className={styles.rowBetween}>
            <div>
              <div className={styles.kicker}>Tenant</div>
              <h2 className={styles.h2}>{loading ? "Loading..." : data?.name}</h2>
              {!loading && data && (<div className={styles.muted}>ID {data.id.slice(0,8)}</div>)}
            </div>
            {/* <div style={{textAlign: "right"}}>
              <div className={styles.kicker}>Wallet balance</div>
              <div className={styles.h2}>{loading ? "—" : fmtKES(data?.wallet_balance)}</div>
            </div> */}
          </div>
          <div className={styles.actionsRow}>
            <a className="btn btn-primary" href="/dashboard/wallet">Go to wallet</a>
            {/* <a className="btn btn-ghost" href="/receipt">Recent receipt</a> */}
          </div>
        </section>

        {/* Fancy wallet card */}
        <section>
          <WalletCard
            name={loading ? "" : data?.name}
            accountNo={loading ? "" : data?.config?.account_no}
            balanceLabel="Balance"
            balanceValue={loading ? null : data?.wallet_balance}
          />
        </section>

        <section className={styles.card}>
          <div className={styles.rowBetween}>
            <div style={{fontWeight: 700}}>Configuration</div>
            {!loading && (
              editing ? (
                <div style={{display: "flex", gap: 8}}>
                  <button className="btn btn-ghost" onClick={() => { setEditing(false); setError(""); }} disabled={saving}>Cancel</button>
                  <button className="btn btn-primary" onClick={onSaveConfig} disabled={saving}>{saving ? "Saving..." : "Save"}</button>
                </div>
              ) : (
                <button className="btn btn-ghost" onClick={() => setEditing(true)}>Edit</button>
              )
            )}
          </div>
          {loading && (<>
            <div className={styles.skeletonLine} />
            <div className={styles.skeletonLine} />
            <div className={styles.skeletonLine} />
          </>)}
          {!loading && data && (
            editing ? (
              <ConfigForm form={form} setForm={setForm} />
            ) : (
              <ConfigRows config={data.config} />
            )
          )}
          {error && (<div style={{color: "#b42318", fontSize: 13}}>{error}</div>)}
        </section>
      </main>
      {confirmAutoPayoutOpen && (
        <ConfirmModal onCancel={() => { setConfirmAutoPayoutOpen(false); }} onConfirm={async () => { setConfirmAutoPayoutOpen(false); await performSave(); }} payoutMethod={form.payment_method} />
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className={"row"} style={{display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", color: "#1f2340"}}>
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  );
}

function ConfigRows({ config }) {
  if (!config) return null;
  const rows = [];

  if (config.account_no) rows.push({ label: "Account", value: config.account_no });
  if (config.link_id) rows.push({ label: "Link", value: config.link_id });
  if (Object.prototype.hasOwnProperty.call(config, "callback_url")) rows.push({ label: "Callback", value: config.callback_url ?? "—" });
  if (Object.prototype.hasOwnProperty.call(config, "auto_payout")) rows.push({ label: "Auto payout", value: config.auto_payout ? "Enabled" : "Disabled" });

  const pm = config.payment_method || {};
  if (pm.mpesa_number) rows.push({ label: "M-Pesa", value: pm.mpesa_number });
  if (pm.paybill_number) rows.push({ label: "Paybill", value: pm.paybill_number });
  if (pm.account_number) rows.push({ label: "Account No.", value: pm.account_number });

  if (rows.length === 0) return <div className={"row"} style={{color: "#657090"}}>No configuration set.</div>;
  return (
    <>
      {rows.map((r, i) => (<Row key={`${r.label}-${i}`} label={r.label} value={r.value} />))}
    </>
  );
}

function ConfigForm({ form, setForm }) {
  const hasPayoutMethod = Boolean(
    form.payment_method?.mpesa_number ||
    form.payment_method?.paybill_number ||
    form.payment_method?.account_number
  );
  return (
    <div style={{display: "grid", gap: 12}}>
      <label className="stack">
        <span style={{fontSize: 12, color: "#657090"}}>Callback URL</span>
        <input className="input" placeholder="https://callback.url" value={form.callback_url} onChange={(e)=>setForm({...form, callback_url: e.target.value})} />
      </label>
      <label className="stack" style={{display: "flex", gap: 8, alignItems: "center"}}>
        <input
          type="checkbox"
          checked={Boolean(form.auto_payout) && hasPayoutMethod}
          onChange={(e)=>setForm({ ...form, auto_payout: e.target.checked })}
          disabled={!hasPayoutMethod}
        />
        <span>
          <strong>Enable auto payout</strong>
          <div style={{fontSize: 12, color: "#657090"}}>
            {hasPayoutMethod ? "Automatically payout using your configured payout method." : "Add a payout method to enable auto payout."}
          </div>
        </span>
      </label>
      <div style={{display: "grid", gap: 8, gridTemplateColumns: "repeat(3, 1fr)"}}>
        <label className="stack">
          <span style={{fontSize: 12, color: "#657090"}}>M-Pesa number</span>
          <input className="input" placeholder="2547********" value={form.payment_method.mpesa_number} onChange={(e)=>setForm({ ...form, payment_method: { ...form.payment_method, mpesa_number: e.target.value } })} />
        </label>
        <label className="stack">
          <span style={{fontSize: 12, color: "#657090"}}>Paybill</span>
          <input className="input" placeholder="1223" value={form.payment_method.paybill_number} onChange={(e)=>setForm({ ...form, payment_method: { ...form.payment_method, paybill_number: e.target.value } })} />
        </label>
        <label className="stack">
          <span style={{fontSize: 12, color: "#657090"}}>Account No.</span>
          <input className="input" placeholder="1234" value={form.payment_method.account_number} onChange={(e)=>setForm({ ...form, payment_method: { ...form.payment_method, account_number: e.target.value } })} />
        </label>
      </div>
    </div>
  );
}

async function onSaveConfig(e) {
  e?.preventDefault?.();
}

function ConfirmModal({ onCancel, onConfirm, payoutMethod }) {
  const methodLabel = (() => {
    if (payoutMethod?.mpesa_number) return `M-Pesa ${payoutMethod.mpesa_number}`;
    if (payoutMethod?.paybill_number && payoutMethod?.account_number) return `Paybill ${payoutMethod.paybill_number} • Acc ${payoutMethod.account_number}`;
    if (payoutMethod?.paybill_number) return `Paybill ${payoutMethod.paybill_number}`;
    if (payoutMethod?.account_number) return `Account ${payoutMethod.account_number}`;
    return "your payout method";
  })();
  return (
    <div style={{position: "fixed", inset: 0, background: "rgba(17,19,38,0.48)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50}}>
      <div style={{background: "#fff", borderRadius: 12, padding: 20, width: "min(520px, 92vw)", boxShadow: "0 10px 30px rgba(0,0,0,0.2)"}} role="dialog" aria-modal="true">
        <div style={{fontSize: 18, fontWeight: 700, marginBottom: 8}}>Enable automatic payouts?</div>
        <div style={{fontSize: 14, color: "#475467", lineHeight: 1.5}}>
          When enabled, payouts will be sent <strong>automatically every Friday</strong> to {methodLabel}.
          Make sure these details are correct. You can change them anytime.
        </div>
        <div style={{display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16}}>
          <button className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="btn btn-primary" onClick={onConfirm}>Accept & Enable</button>
        </div>
      </div>
    </div>
  );
}

function WalletCard({ name, accountNo, balanceLabel, balanceValue }) {
  const masked = accountNo ? String(accountNo).replace(/.(?=.{4})/g, "•") : "••••";
  return (
    <div className={styles.walletCard}>
      <div className={styles.glow1} />
      <div className={styles.glow2} />
      <div className={styles.walletHeader}>
        <div className={styles.brandMark}>Paytrack Wallet</div>
        <div className={styles.chip}>
          <div className={styles.chipBoxA} />
          <div className={styles.chipBoxB} />
        </div>
      </div>

      <div className={styles.walletBody}>
        <div className={styles.label}>Tenant</div>
        <div className={styles.holder}>{name || "—"}</div>
        <div className={styles.infoRow}>
          <div>
            <div className={styles.subLabel}>Account</div>
            <div className={styles.mono}>{masked}</div>
          </div>
          <div className={styles.amount}>
            <div className={styles.subLabel}>{balanceLabel}</div>
            {balanceValue == null ? "—" : `KES ${Number(balanceValue).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`}
          </div>
        </div>
      </div>
    </div>
  );
}


