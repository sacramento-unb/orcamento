import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  Download,
  FileSpreadsheet,
  LayoutDashboard,
  Landmark,
  LogOut,
  Menu,
  Pencil,
  Plus,
  ReceiptText,
  RefreshCw,
  Repeat2,
  Search,
  Sparkles,
  Trash2,
  TrendingUp,
  Upload,
  WalletCards,
  X,
} from "lucide-react";
import { api } from "./api";

const CATEGORY_COLORS = ["#e5a849", "#49a789", "#ee7c65", "#72a5d7", "#a18bd0", "#b7b85d"];
const CATEGORIES = [
  "Moradia",
  "Alimentação",
  "Transporte",
  "Saúde",
  "Educação",
  "Lazer",
  "Assinaturas",
  "Proteção",
  "Salário",
  "Investimentos",
  "Outros",
];
const MONTHS = [
  ["Jan", "Janeiro"],
  ["Fev", "Fevereiro"],
  ["Mar", "Março"],
  ["Abr", "Abril"],
  ["Mai", "Maio"],
  ["Jun", "Junho"],
  ["Jul", "Julho"],
  ["Ago", "Agosto"],
  ["Set", "Setembro"],
  ["Out", "Outubro"],
  ["Nov", "Novembro"],
  ["Dez", "Dezembro"],
];
const YEARS = Array.from({ length: 81 }, (_, index) => String(2020 + index));

const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function OrcaIcon({ size = 24 }) {
  return (
    <svg
      aria-hidden="true"
      className="orca-icon"
      width={size}
      height={size}
      viewBox="0 0 64 44"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M13 17.5C19 10.2 31.5 8 43.5 10.7C51 12.4 57.2 16.5 60.5 21C57.2 25.6 50.6 28.8 42 30.2C31.3 32 21 29.6 13.8 25.2L6.3 31.2L8.2 23.3L1.5 19.7L9.1 16.9L5.4 8.7L14.1 14.8C13.6 15.7 13.2 16.6 13 17.5Z"
        fill="#111111"
      />
      <path
        d="M25.1 10.1C26.7 4.7 30.6 0.8 34 0.5C35.7 3.4 35.8 7.2 34.7 9.6C31.5 9.2 28.2 9.4 25.1 10.1Z"
        fill="#111111"
      />
      <path
        d="M35.5 29.9C32.4 36.4 27.5 41.8 23.5 43C22.6 38.1 25.6 32.9 29.1 30C31.2 30.2 33.4 30.2 35.5 29.9Z"
        fill="#111111"
      />
      <path
        d="M14.2 23.8C23.3 28.3 39.1 30.5 52.5 24.5C48.7 29.1 41.6 31.6 33.7 31.9C25.8 32.2 18.5 29.6 13.8 25.2L14.2 23.8Z"
        fill="#ffffff"
      />
      <path
        d="M45.1 13.5C49.4 12.6 53.5 14.1 55.3 16.8C52.7 19.2 48.6 19.6 45.2 17.4C44.3 16.1 44.3 14.7 45.1 13.5Z"
        fill="#ffffff"
      />
      <circle cx="56.3" cy="20.5" r="1.1" fill="#ffffff" />
    </svg>
  );
}

function currentMonth() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonth(month, short = false) {
  if (!month) return "";
  const [year, number] = month.split("-").map(Number);
  return new Intl.DateTimeFormat("pt-BR", {
    month: short ? "short" : "long",
    year: short ? undefined : "numeric",
  })
    .format(new Date(year, number - 1, 1))
    .replace(".", "");
}

function formatDate(dateString) {
  if (!dateString) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateString));
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      {label && <span>{label}</span>}
      {payload.map((item) => (
        <div key={item.dataKey || item.name}>
          <i style={{ background: item.color || item.payload?.fill }} />
          <strong>{item.name}</strong>
          <b>{currency.format(item.value)}</b>
        </div>
      ))}
    </div>
  );
}

function EmptyChart() {
  return (
    <div className="empty-chart">
      <BarChart3 size={28} />
      <span>Sem dados neste período</span>
    </div>
  );
}

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await onLogin({ username, password });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand"><span className="brand-mark"><OrcaIcon size={30} /></span><strong>Orca</strong></div>
        <span className="eyebrow">Acesso privado</span>
        <h1>Suas finanças, no lugar certo.</h1>
        <p>Entre para acessar o orçamento mensal e os investimentos.</p>
        <form onSubmit={submit}>
          <label className="field">
            <span>Usuário</span>
            <input autoFocus required value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label className="field">
            <span>Senha</span>
            <input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error && <div className="login-error" role="alert">{error}</div>}
          <button className="primary-button login-button" disabled={loading}>
            {loading ? <RefreshCw className="spin" size={17} /> : <Check size={17} />}
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}

function SummaryCard({ label, value, icon: Icon, tone, detail, formatter = currency.format }) {
  return (
    <article className={`summary-card ${tone}`}>
      <div className="summary-label">
        <span className="summary-icon">
          <Icon size={17} />
        </span>
        {label}
      </div>
      <strong>{formatter(value)}</strong>
      <small>{detail}</small>
    </article>
  );
}

function MonthTabs({ month, onChange }) {
  const year = month.slice(0, 4);
  const selectedNumber = Number(month.slice(5));
  return (
    <nav className="month-tabs" aria-label="Meses do ano">
      {MONTHS.map(([shortName, fullName], index) => {
        const number = index + 1;
        return (
          <button
            key={fullName}
            className={selectedNumber === number ? "active" : ""}
            onClick={() => onChange(`${year}-${String(number).padStart(2, "0")}`)}
            aria-label={`Ver ${fullName} de ${year}`}
          >
            <span>{shortName}</span>
            <small>{fullName}</small>
          </button>
        );
      })}
    </nav>
  );
}

function Dashboard({ summary, loading }) {
  const totalCategories = summary?.category_totals?.reduce(
    (total, item) => total + item.amount,
    0,
  );
  const highestCategory = summary?.category_totals?.[0];

  if (loading && !summary) {
    return (
      <div className="loading-state">
        <RefreshCw className="spin" size={28} />
        <span>Organizando seus números…</span>
      </div>
    );
  }

  return (
    <>
      <section className="summary-grid">
        <SummaryCard
          label="Receitas"
          value={summary?.income || 0}
          icon={ArrowUpRight}
          tone="income"
          detail={`${summary?.entries_count || 0} lançamentos ativos`}
        />
        <SummaryCard
          label="Gastos"
          value={summary?.expenses || 0}
          icon={ArrowDownRight}
          tone="expense"
          detail={
            summary?.income
              ? `${((summary.expenses / summary.income) * 100).toFixed(1)}% da renda`
              : "do mês selecionado"
          }
        />
        <SummaryCard
          label="Saldo atual"
          value={summary?.balance || 0}
          icon={WalletCards}
          tone="balance"
          detail={summary?.balance >= 0 ? "antes do plano recomendado" : "atenção ao orçamento"}
        />
        <SummaryCard
          label="Taxa atual"
          value={summary?.savings_rate || 0}
          icon={TrendingUp}
          tone="rate"
          formatter={(value) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value)}
          detail="% ainda não lançada"
        />
      </section>

      <section className="dashboard-grid">
        <article className="panel trend-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Fluxo mensal</span>
              <h2>Receitas e gastos</h2>
            </div>
            <div className="legend">
              <span><i className="income-dot" />Receitas</span>
              <span><i className="expense-dot" />Gastos</span>
            </div>
          </div>
          <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={summary?.history || []} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#49a789" stopOpacity={0.32} />
                    <stop offset="100%" stopColor="#49a789" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ee7c65" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#ee7c65" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#dce2dc" strokeDasharray="3 6" vertical={false} />
                <XAxis
                  dataKey="month"
                  tickFormatter={(value) => formatMonth(value, true)}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#728078", fontSize: 12 }}
                />
                <YAxis
                  width={54}
                  tickFormatter={(value) => `${Math.round(value / 1000)}k`}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#728078", fontSize: 12 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="income"
                  name="Receitas"
                  stroke="#287a64"
                  strokeWidth={2.5}
                  fill="url(#incomeGradient)"
                />
                <Area
                  type="monotone"
                  dataKey="expenses"
                  name="Gastos"
                  stroke="#da654f"
                  strokeWidth={2.5}
                  fill="url(#expenseGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel category-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Distribuição</span>
              <h2>Por categoria</h2>
            </div>
          </div>
          {summary?.category_totals?.length ? (
            <>
              <div className="donut-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={summary.category_totals}
                      dataKey="amount"
                      nameKey="category"
                      innerRadius={63}
                      outerRadius={89}
                      paddingAngle={3}
                      stroke="none"
                    >
                      {summary.category_totals.map((item, index) => (
                        <Cell
                          key={item.category}
                          fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="donut-center">
                  <span>Total</span>
                  <strong>{currency.format(totalCategories || 0)}</strong>
                </div>
              </div>
              <div className="category-legend">
                {summary.category_totals.map((item, index) => (
                  <div key={item.category}>
                    <span>
                      <i style={{ background: CATEGORY_COLORS[index % CATEGORY_COLORS.length] }} />
                      {item.category}
                    </span>
                    <strong>{currency.format(item.amount)}</strong>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyChart />
          )}
        </article>

        <article className="panel breakdown-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Comparativo</span>
              <h2>Peso de cada gasto</h2>
            </div>
          </div>
          {summary?.category_totals?.length ? (
            <div className="bar-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={summary.category_totals}
                  layout="vertical"
                  margin={{ top: 4, right: 18, left: 12, bottom: 0 }}
                >
                  <CartesianGrid stroke="#dce2dc" strokeDasharray="3 6" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(value) => `${Math.round(value / 1000)}k`}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#728078", fontSize: 12 }}
                  />
                  <YAxis
                    dataKey="category"
                    type="category"
                    width={85}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#2a3832", fontSize: 12 }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="amount" name="Gastos" radius={[0, 6, 6, 0]} barSize={18}>
                    {summary.category_totals.map((item, index) => (
                      <Cell
                        key={item.category}
                        fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyChart />
          )}
        </article>

        <article className="insight-card">
          <span className="insight-icon"><Sparkles size={20} /></span>
          <div>
            <span className="eyebrow">Leitura rápida</span>
            <h2>
              {summary?.balance >= 0
                ? `Você preserva ${summary?.savings_rate || 0}% da renda mensal.`
                : "Os gastos ultrapassam a renda neste mês."}
            </h2>
            <p>
              {highestCategory
                ? `${highestCategory.category} é a maior categoria, com ${currency.format(highestCategory.amount)} em gastos.`
                : "Adicione seus lançamentos para receber uma leitura do orçamento."}
            </p>
          </div>
        </article>
      </section>
    </>
  );
}

function PlanSection({ plan }) {
  if (!plan) return null;
  const allocation = (key) => plan.allocations.find((item) => item.key === key);
  const formatPercent = (amount) => `${((amount / plan.income_total) * 100).toFixed(1)}%`;

  return (
    <section className="plan-section">
      <div className="plan-title">
        <div>
          <span className="eyebrow">Plano recomendado</span>
          <h2>Destino da renda mensal</h2>
        </div>
        <span className="plan-total">{currency.format(plan.income_total)} de renda</span>
      </div>

      <div className="plan-grid">
        <article className="panel plan-overview">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Distribuição</span>
              <h2>Orçamento base</h2>
            </div>
          </div>
          <div className="plan-list">
            <div className="plan-row fixed-row">
              <span><i />Gastos fixos informados</span>
              <strong>{currency.format(plan.fixed_total)}</strong>
              <small>{formatPercent(plan.fixed_total)}</small>
            </div>
            <div className="plan-row preserved-row">
              <span><i />{plan.preserved_theoretical.description}</span>
              <strong>{currency.format(plan.preserved_theoretical.amount)}</strong>
              <small>{formatPercent(plan.preserved_theoretical.amount)}</small>
            </div>
            {plan.allocations.map((item) => (
              <div className="plan-row" key={item.key}>
                <span><i className={`plan-dot ${item.key}`} />{item.description}</span>
                <strong>{currency.format(item.amount)}</strong>
                <small>{formatPercent(item.amount)}</small>
              </div>
            ))}
          </div>
          <div className="plan-total-row">
            <span>Saldo não destinado · direcionado ao imóvel</span>
            <strong>{currency.format(plan.free_balance)}</strong>
          </div>
        </article>

        <article className="panel goal-card property-goal">
          <span className="goal-label">Compra do imóvel próprio</span>
          <strong>{currency.format(allocation("property").amount)}<small>/mês</small></strong>
          <p>{currency.format(allocation("property").amount * 12)} em 12 meses para entrada e custos.</p>
          <span className="goal-note">Separar do restante da carteira e revisar a meta com o valor do imóvel.</span>
        </article>

        <article className="panel goal-card retirement-goal">
          <span className="goal-label">Aposentadoria turbinada</span>
          <strong>{currency.format(allocation("retirement").amount)}<small>/mês</small></strong>
          <p>{formatPercent(allocation("retirement").amount)} da renda em aportes de longo prazo.</p>
          <span className="goal-note">Manter constância e ajustar a carteira ao perfil de risco.</span>
        </article>

        <article className="panel goal-card investment-goal">
          <span className="goal-label">Investimentos</span>
          <strong>{currency.format(allocation("investments").amount)}<small>/mês</small></strong>
          <p>Além do imóvel e da aposentadoria, para diversificação e objetivos médios.</p>
          <span className="goal-note">Registre aplicações na tela Investimentos quando importar o banco.</span>
        </article>

        <article className="panel property-chart-card">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Compra do imóvel próprio</span>
              <h2>Patrimônio projetado</h2>
            </div>
            <span className="chart-assumption">
              100% CDI · {(plan.cdi_annual_rate * 100).toFixed(1)}% a.a.
            </span>
          </div>
          <div className="property-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={plan.property_projection} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="propertyGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#a18bd0" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#a18bd0" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e6ebe5" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="month"
                  tickFormatter={(value) => (value === 0 ? "Hoje" : value % 12 === 0 ? `${value / 12}a` : "")}
                  tick={{ fill: "#87938d", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(value) => `${Math.round(value / 1000)}k`}
                  tick={{ fill: "#87938d", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={36}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="balance"
                  name="Patrimônio projetado"
                  stroke="#8e73c3"
                  strokeWidth={2.5}
                  fill="url(#propertyGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-note">
            Projeção de 60 meses com o aporte mensal do fundo, juros compostos mensais equivalentes à premissa de 100% do CDI e aportes no fim de cada mês. Ajuste <code>ORCA_CDI_ANNUAL_RATE</code> quando quiser atualizar a taxa.
          </p>
        </article>
      </div>
    </section>
  );
}

function EntryModal({ entry, month, mode, onClose, onSave, saving }) {
  const [form, setForm] = useState(
    entry || {
      description: "",
      amount: "",
      entry_type: "expense",
      category: "Moradia",
      recurring: mode !== "monthly",
      start_month: month,
      end_month: "",
      notes: "",
    },
  );

  const setField = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  function submit(event) {
    event.preventDefault();
    onSave({ ...form, amount: Number(form.amount), end_month: form.end_month || null });
  }

  const creationTitle =
    mode === "monthly" ? "Adicionar gasto deste mês" : "Adicionar gasto fixo";

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="entry-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="entry-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <span className="eyebrow">
              {entry
                ? "Editar lançamento"
                : mode === "monthly"
                  ? `Gasto de ${formatMonth(month)}`
                  : "Novo gasto fixo"}
            </span>
            <h2 id="entry-title">{entry ? entry.description : creationTitle}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Fechar">
            <X size={19} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="type-selector">
            <button
              type="button"
              className={form.entry_type === "expense" ? "active expense" : ""}
              onClick={() => setField("entry_type", "expense")}
            >
              <ArrowDownRight size={17} /> Gasto
            </button>
            <button
              type="button"
              className={form.entry_type === "income" ? "active income" : ""}
              onClick={() => setField("entry_type", "income")}
            >
              <ArrowUpRight size={17} /> Receita
            </button>
          </div>

          <label className="field full">
            <span>Descrição</span>
            <input
              autoFocus
              required
              value={form.description}
              onChange={(event) => setField("description", event.target.value)}
              placeholder="Ex.: Aluguel"
            />
          </label>

          <div className="form-row">
            <label className="field">
              <span>Valor mensal</span>
              <div className="money-input">
                <span>R$</span>
                <input
                  required
                  min="0.01"
                  step="0.01"
                  type="number"
                  value={form.amount}
                  onChange={(event) => setField("amount", event.target.value)}
                  placeholder="0,00"
                />
              </div>
            </label>
            <label className="field">
              <span>Categoria</span>
              <div className="select-wrap">
                <select
                  value={form.category}
                  onChange={(event) => setField("category", event.target.value)}
                >
                  {CATEGORIES.map((category) => (
                    <option key={category}>{category}</option>
                  ))}
                </select>
                <ChevronDown size={16} />
              </div>
            </label>
          </div>

          <label className="toggle-row">
            <span>
              <strong>Repetir todos os meses</strong>
              <small>Ideal para gastos e receitas fixas.</small>
            </span>
            <input
              type="checkbox"
              checked={form.recurring}
              onChange={(event) => setField("recurring", event.target.checked)}
            />
            <i />
          </label>

          <div className="form-row">
            <label className="field">
              <span>{form.recurring ? "Começa em" : "Mês do lançamento"}</span>
              <input
                required
                type="month"
                value={form.start_month}
                onChange={(event) => setField("start_month", event.target.value)}
              />
            </label>
            <label className={`field ${!form.recurring ? "muted-field" : ""}`}>
              <span>Termina em <small>(opcional)</small></span>
              <input
                type="month"
                disabled={!form.recurring}
                value={form.end_month || ""}
                onChange={(event) => setField("end_month", event.target.value)}
              />
            </label>
          </div>

          <label className="field full">
            <span>Observações <small>(opcional)</small></span>
            <textarea
              rows="3"
              value={form.notes || ""}
              onChange={(event) => setField("notes", event.target.value)}
              placeholder="Algum detalhe importante…"
            />
          </label>

          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="primary-button" disabled={saving}>
              {saving ? <RefreshCw className="spin" size={17} /> : <Check size={17} />}
              {saving ? "Salvando…" : "Salvar e exportar"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function BankImportModal({ month, onClose, onImported, onError }) {
  const [preview, setPreview] = useState(null);
  const [reading, setReading] = useState(false);
  const [importing, setImporting] = useState(false);

  async function readFile(file) {
    if (!file) return;
    setReading(true);
    try {
      const result = await api.previewBankFile(file);
      setPreview({
        ...result,
        transactions: result.transactions.map((transaction) => ({
          ...transaction,
          selected: !transaction.duplicate,
        })),
        investments: result.investments.map((investment) => ({
          ...investment,
          selected: !investment.duplicate,
        })),
      });
    } catch (error) {
      onError(error.message);
    } finally {
      setReading(false);
    }
  }

  function updateTransaction(index, changes) {
    setPreview((current) => ({
      ...current,
      transactions: current.transactions.map((transaction, transactionIndex) =>
        transactionIndex === index ? { ...transaction, ...changes } : transaction,
      ),
    }));
  }

  const selectedTransactions = preview?.transactions.filter(
    (transaction) => transaction.selected && !transaction.duplicate,
  ) || [];
  const selectedInvestments = preview?.investments.filter(
    (investment) => investment.selected && !investment.duplicate,
  ) || [];

  async function confirmImport() {
    if (!selectedTransactions.length && !selectedInvestments.length) {
      onError("Selecione ao menos um gasto ou investimento novo.");
      return;
    }
    setImporting(true);
    try {
      const result = await api.confirmBankImport({
        filename: preview.filename,
        selected_month: month,
        transactions: selectedTransactions.map(
          ({ selected: _selected, duplicate: _duplicate, ...item }) => item,
        ),
        investments: selectedInvestments.map(
          ({ selected: _selected, duplicate: _duplicate, ...item }) => item,
        ),
      });
      onImported(result);
    } catch (error) {
      onError(error.message);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="bank-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bank-import-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <span className="eyebrow">Importação bancária</span>
            <h2 id="bank-import-title">Importar gastos e investimentos</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Fechar">
            <X size={19} />
          </button>
        </div>

        {!preview ? (
          <div className="upload-step">
            <label className={reading ? "upload-dropzone reading" : "upload-dropzone"}>
              {reading ? <RefreshCw className="spin" size={29} /> : <Upload size={29} />}
              <strong>{reading ? "Lendo o extrato…" : "Selecione o arquivo exportado pelo banco"}</strong>
              <span>Formatos aceitos: CSV, OFX e XLSX · máximo de 10 MB</span>
              <input
                type="file"
                accept=".csv,.ofx,.xlsx,.xlsm"
                disabled={reading}
                onChange={(event) => readFile(event.target.files?.[0])}
              />
            </label>
            <div className="import-notice">
              <Landmark size={18} />
              <p>
                O arquivo é processado localmente pela aplicação. Gastos entram
                no orçamento e investimentos ficam separados em uma aba própria.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="import-summary">
              <div>
                <span className="file-type">{preview.file_type}</span>
                <strong>{preview.filename}</strong>
              </div>
              <div className="import-stats">
                <span><b>{preview.transactions.length}</b> gastos encontrados</span>
                <span><b>{preview.investments.length}</b> investimentos encontrados</span>
                {preview.ignored_income_count > 0 && (
                  <span><b>{preview.ignored_income_count}</b> receitas ignoradas</span>
                )}
                {preview.duplicate_count > 0 && (
                  <span className="duplicate-stat">
                    <b>{preview.duplicate_count}</b> já importados
                  </span>
                )}
              </div>
            </div>

            {!!preview.transactions.length && (
              <>
                <div className="import-select-bar">
                  <label>
                    <input
                      type="checkbox"
                      checked={
                        preview.transactions.some((item) => !item.duplicate) &&
                        preview.transactions
                          .filter((item) => !item.duplicate)
                          .every((item) => item.selected)
                      }
                      onChange={(event) =>
                        setPreview((current) => ({
                          ...current,
                          transactions: current.transactions.map((transaction) => ({
                            ...transaction,
                            selected: transaction.duplicate ? false : event.target.checked,
                          })),
                        }))
                      }
                    />
                    Selecionar todos os gastos novos
                  </label>
                  <span>{selectedTransactions.length} selecionados</span>
                </div>

                <div className="import-list">
                  {preview.transactions.map((transaction, index) => (
                <div
                  key={`${transaction.external_id}-${index}`}
                  className={`import-transaction ${transaction.duplicate ? "duplicate" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={transaction.selected}
                    disabled={transaction.duplicate}
                    onChange={(event) =>
                      updateTransaction(index, { selected: event.target.checked })
                    }
                    aria-label={`Selecionar ${transaction.description}`}
                  />
                  <div className="transaction-main">
                    <strong>{transaction.description}</strong>
                    <span>
                      {new Intl.DateTimeFormat("pt-BR").format(
                        new Date(`${transaction.date}T12:00:00`),
                      )}
                      {transaction.duplicate && " · já está no banco"}
                    </span>
                    {!!transaction.reconciliation_options?.length && (
                      <label className="reconciliation-choice">
                        <span>Tratamento no orçamento</span>
                        <select
                          value={transaction.reconciled_entry_id || ""}
                          disabled={transaction.duplicate}
                          onChange={(event) =>
                            updateTransaction(index, {
                              reconciled_entry_id: event.target.value
                                ? Number(event.target.value)
                                : null,
                            })
                          }
                        >
                          <option value="">Adicionar separadamente</option>
                          {transaction.reconciliation_options.map((option) => (
                            <option key={option.entry_id} value={option.entry_id}>
                              Conciliar com {option.description} · previsto{" "}
                              {currency.format(option.expected_amount)}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </div>
                  <select
                    value={transaction.category}
                    disabled={transaction.duplicate}
                    onChange={(event) =>
                      updateTransaction(index, { category: event.target.value })
                    }
                    aria-label={`Categoria de ${transaction.description}`}
                  >
                    {CATEGORIES.filter((category) => category !== "Salário").map((category) => (
                      <option key={category}>{category}</option>
                    ))}
                  </select>
                  <strong className="transaction-amount">
                    {currency.format(transaction.amount)}
                  </strong>
                </div>
                  ))}
                </div>
              </>
            )}

            {!!preview.investments.length && (
              <>
                <div className="import-select-bar investment-select-bar">
                  <label>
                    <input
                      type="checkbox"
                      checked={
                        preview.investments.some((item) => !item.duplicate) &&
                        preview.investments
                          .filter((item) => !item.duplicate)
                          .every((item) => item.selected)
                      }
                      onChange={(event) =>
                        setPreview((current) => ({
                          ...current,
                          investments: current.investments.map((investment) => ({
                            ...investment,
                            selected: investment.duplicate ? false : event.target.checked,
                          })),
                        }))
                      }
                    />
                    Selecionar todos os investimentos novos
                  </label>
                  <span>{selectedInvestments.length} selecionados</span>
                </div>
                <div className="import-list investment-import-list">
                  {preview.investments.map((investment, index) => (
                    <div
                      key={`${investment.external_id}-${index}`}
                      className={`import-transaction investment-transaction ${
                        investment.duplicate ? "duplicate" : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={investment.selected}
                        disabled={investment.duplicate}
                        onChange={(event) =>
                          setPreview((current) => ({
                            ...current,
                            investments: current.investments.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, selected: event.target.checked }
                                : item,
                            ),
                          }))
                        }
                        aria-label={`Selecionar ${investment.description}`}
                      />
                      <div className="transaction-main">
                        <strong>{investment.asset}</strong>
                        <span>
                          {investment.movement_type} ·{" "}
                          {new Intl.DateTimeFormat("pt-BR").format(
                            new Date(`${investment.date}T12:00:00`),
                          )}
                          {investment.duplicate && " · já importado"}
                        </span>
                        {investment.description !== investment.asset && (
                          <small>{investment.description}</small>
                        )}
                      </div>
                      <strong className="transaction-amount">
                        {currency.format(investment.amount)}
                      </strong>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="modal-actions bank-actions">
              <button className="secondary-button" onClick={() => setPreview(null)}>
                Escolher outro arquivo
              </button>
              <button
                className="primary-button"
                disabled={
                  (!selectedTransactions.length && !selectedInvestments.length) ||
                  importing
                }
                onClick={confirmImport}
              >
                {importing ? <RefreshCw className="spin" size={17} /> : <Check size={17} />}
                {importing
                  ? "Importando…"
                  : `Importar ${
                      selectedTransactions.length + selectedInvestments.length
                    } registros`}
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function Investments({ investments, loading, onBankImport }) {
  const totals = useMemo(
    () =>
      investments.reduce(
        (result, investment) => {
          if (investment.movement_type === "Aplicação") {
            result.applications += investment.amount;
          } else if (investment.movement_type === "Resgate") {
            result.redemptions += investment.amount;
          } else if (investment.movement_type === "Rendimento") {
            result.income += investment.amount;
          }
          return result;
        },
        { applications: 0, redemptions: 0, income: 0 },
      ),
    [investments],
  );

  return (
    <section className="investments-page">
      <section className="summary-grid investment-summary-grid">
        <SummaryCard
          label="Aplicações"
          value={totals.applications}
          icon={ArrowUpRight}
          tone="balance"
          detail="total aportado no ano"
        />
        <SummaryCard
          label="Resgates"
          value={totals.redemptions}
          icon={ArrowDownRight}
          tone="income"
          detail="total retirado no ano"
        />
        <SummaryCard
          label="Rendimentos"
          value={totals.income}
          icon={TrendingUp}
          tone="rate"
          detail="rendimentos identificados"
        />
      </section>

      <article className="panel entries-panel investment-panel">
        <div className="table-toolbar">
          <div>
            <span className="eyebrow">Patrimônio separado do orçamento</span>
            <h2>Movimentações de investimentos</h2>
          </div>
          <button className="primary-button" onClick={onBankImport}>
            <Landmark size={17} /> Importar arquivo do banco
          </button>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Ativo / produto</th>
                <th>Movimentação</th>
                <th>Detalhes</th>
                <th className="align-right">Valor</th>
              </tr>
            </thead>
            <tbody>
              {investments.map((investment) => (
                <tr key={investment.id}>
                  <td>
                    {new Intl.DateTimeFormat("pt-BR").format(
                      new Date(`${investment.date}T12:00:00`),
                    )}
                  </td>
                  <td>
                    <div className="entry-name">
                      <span className="entry-direction investment">
                        <TrendingUp size={16} />
                      </span>
                      <div>
                        <strong>{investment.asset}</strong>
                        <small>{investment.source_file}</small>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="investment-movement">
                      {investment.movement_type}
                    </span>
                  </td>
                  <td>
                    <span>{investment.description}</span>
                    {(investment.quantity || investment.unit_price) && (
                      <small className="investment-details">
                        {investment.quantity
                          ? `${new Intl.NumberFormat("pt-BR", {
                              maximumFractionDigits: 8,
                            }).format(investment.quantity)} unidades`
                          : ""}
                        {investment.quantity && investment.unit_price ? " · " : ""}
                        {investment.unit_price
                          ? `${currency.format(investment.unit_price)} por unidade`
                          : ""}
                      </small>
                    )}
                  </td>
                  <td className="align-right amount investment">
                    {currency.format(investment.amount)}
                  </td>
                </tr>
              ))}
              {!investments.length && !loading && (
                <tr>
                  <td colSpan="5">
                    <div className="empty-table">
                      <TrendingUp size={28} />
                      <strong>Nenhum investimento importado</strong>
                      <span>
                        Importe o arquivo do banco para trazer aplicações,
                        resgates e rendimentos.
                      </span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

function Editor({
  entries,
  exports,
  month,
  loading,
  onAddFixed,
  onAddMonthly,
  onBankImport,
  onEdit,
  onDelete,
  onExport,
  exporting,
}) {
  const [search, setSearch] = useState("");
  const [type, setType] = useState("all");
  const [deleteTarget, setDeleteTarget] = useState(null);

  const filtered = useMemo(
    () =>
      entries.filter((entry) => {
        const matchesSearch = `${entry.description} ${entry.category}`
          .toLocaleLowerCase("pt-BR")
          .includes(search.toLocaleLowerCase("pt-BR"));
        return matchesSearch && (type === "all" || entry.entry_type === type);
      }),
    [entries, search, type],
  );

  const latestExport = exports[0];

  return (
    <section className="editor-page">
      <article className="export-banner">
        <div className="export-mark"><FileSpreadsheet size={22} /></div>
        <div>
          <span className="eyebrow">Sincronização com a planilha</span>
          <h2>{latestExport ? "Última versão pronta" : "Gere sua primeira versão"}</h2>
          <p>
            {latestExport
              ? `${latestExport.filename} · ${formatDate(latestExport.created_at)}`
              : "Toda alteração salva cria automaticamente um novo arquivo Excel."}
          </p>
        </div>
        <div className="export-actions">
          {latestExport && (
            <a className="secondary-button" href={api.downloadUrl(latestExport.url)}>
              <Download size={17} /> Baixar última
            </a>
          )}
          <button className="primary-button" onClick={onExport} disabled={exporting}>
            {exporting ? <RefreshCw className="spin" size={17} /> : <FileSpreadsheet size={17} />}
            Exportar agora
          </button>
        </div>
      </article>

      <article className="panel entries-panel">
        <div className="table-toolbar">
          <div>
            <span className="eyebrow">Base de dados</span>
            <h2>Todos os lançamentos</h2>
          </div>
          <div className="new-expense-actions">
            <button className="secondary-button bank-import-button" onClick={onBankImport}>
              <Landmark size={17} /> Importar do banco
            </button>
            <button className="primary-button" onClick={onAddFixed}>
              <Repeat2 size={16} /> Novo gasto fixo
            </button>
            <button className="secondary-button" onClick={onAddMonthly}>
              <Plus size={17} /> Gasto do mês
            </button>
          </div>
        </div>

        <div className="filters">
          <label className="search-field">
            <Search size={17} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nome ou categoria"
            />
          </label>
          <div className="segmented-filter">
            {[
              ["all", "Todos"],
              ["expense", "Gastos"],
              ["income", "Receitas"],
            ].map(([value, label]) => (
              <button
                key={value}
                className={type === value ? "active" : ""}
                onClick={() => setType(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="result-count">{filtered.length} itens</span>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Descrição</th>
                <th>Categoria</th>
                <th>Frequência</th>
                <th>Início</th>
                <th className="align-right">Valor</th>
                <th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry) => (
                <tr key={entry.id}>
                  <td>
                    <div className="entry-name">
                      <span className={`entry-direction ${entry.entry_type}`}>
                        {entry.entry_type === "expense" ? (
                          <ArrowDownRight size={16} />
                        ) : (
                          <ArrowUpRight size={16} />
                        )}
                      </span>
                      <div>
                        <strong>{entry.description}</strong>
                        {entry.notes && <small>{entry.notes}</small>}
                      </div>
                    </div>
                  </td>
                  <td><span className="category-pill">{entry.category}</span></td>
                  <td>
                    <span
                      className={
                        entry.reconciled_entry_id
                          ? "reconciled-badge"
                          : entry.recurring
                            ? "recurring-badge"
                            : "single-badge"
                      }
                    >
                      {entry.reconciled_entry_id
                        ? "Real conciliado"
                        : entry.recurring
                          ? "Mensal"
                          : "Pontual"}
                    </span>
                  </td>
                  <td>{formatMonth(entry.start_month, true)} {entry.start_month.slice(0, 4)}</td>
                  <td className={`align-right amount ${entry.entry_type}`}>
                    {entry.entry_type === "expense" ? "− " : "+ "}
                    {currency.format(entry.amount)}
                  </td>
                  <td>
                    <div className="row-actions">
                      <button onClick={() => onEdit(entry)} aria-label={`Editar ${entry.description}`}>
                        <Pencil size={16} />
                      </button>
                      <button
                        className="delete"
                        onClick={() => setDeleteTarget(entry)}
                        aria-label={`Excluir ${entry.description}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!filtered.length && !loading && (
                <tr>
                  <td colSpan="6">
                    <div className="empty-table">
                      <ReceiptText size={28} />
                      <strong>Nenhum lançamento encontrado</strong>
                      <span>Ajuste os filtros ou adicione um novo item.</span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>

      {deleteTarget && (
        <div className="modal-backdrop" onMouseDown={() => setDeleteTarget(null)}>
          <section className="confirm-modal" onMouseDown={(event) => event.stopPropagation()}>
            <span className="danger-icon"><Trash2 size={22} /></span>
            <h2>Excluir “{deleteTarget.description}”?</h2>
            <p>O lançamento será removido do banco e uma nova planilha será gerada.</p>
            <div className="modal-actions">
              <button className="secondary-button" onClick={() => setDeleteTarget(null)}>
                Cancelar
              </button>
              <button
                className="danger-button"
                onClick={() => {
                  onDelete(deleteTarget);
                  setDeleteTarget(null);
                }}
              >
                <Trash2 size={17} /> Excluir e exportar
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

export default function App() {
  const [auth, setAuth] = useState({ loading: true, user: null });
  const [tab, setTab] = useState("dashboard");
  const [month, setMonth] = useState(currentMonth());
  const [summary, setSummary] = useState(null);
  const [plan, setPlan] = useState(null);
  const [entries, setEntries] = useState([]);
  const [investments, setInvestments] = useState([]);
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalEntry, setModalEntry] = useState(undefined);
  const [newEntryMode, setNewEntryMode] = useState("fixed");
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [toast, setToast] = useState(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [bankModalOpen, setBankModalOpen] = useState(false);

  useEffect(() => {
    api.me()
      .then((result) => setAuth({ loading: false, user: result.user || null }))
      .catch(() => setAuth({ loading: false, user: null }));
  }, []);

  async function login(credentials) {
    const result = await api.login(credentials);
    setAuth({ loading: false, user: result.user });
  }

  async function logout() {
    await api.logout();
    setAuth({ loading: false, user: null });
  }

  const showToast = useCallback((message, kind = "success") => {
    setToast({ message, kind });
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, planData, entriesData, investmentsData, exportsData] = await Promise.all([
        api.summary(month),
        api.plan(month),
        api.entries(),
        api.investments(month.slice(0, 4)),
        api.exports(),
      ]);
      setSummary(summaryData);
      setPlan(planData);
      setEntries(entriesData);
      setInvestments(investmentsData);
      setExports(exportsData);
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setLoading(false);
    }
  }, [month, showToast]);

  useEffect(() => {
    if (!auth.user) return undefined;
    loadAll();
  }, [auth.user, loadAll]);

  if (auth.loading) {
    return <div className="loading-state"><RefreshCw className="spin" size={28} /><span>Carregando…</span></div>;
  }
  if (!auth.user) return <Login onLogin={login} />;

  async function saveEntry(entry) {
    setSaving(true);
    try {
      const result = modalEntry?.id
        ? await api.updateEntry(modalEntry.id, entry)
        : await api.createEntry(entry);
      setModalOpen(false);
      setExports((current) => [result.export, ...current]);
      showToast("Salvo. Uma nova versão da planilha foi criada.");
      await loadAll();
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setSaving(false);
    }
  }

  async function deleteEntry(entry) {
    try {
      const result = await api.deleteEntry(entry.id, month);
      setExports((current) => [result.export, ...current]);
      showToast("Lançamento excluído e planilha atualizada.");
      await loadAll();
    } catch (error) {
      showToast(error.message, "error");
    }
  }

  async function exportNow() {
    setExporting(true);
    try {
      const result = await api.export(month);
      setExports((current) => [result, ...current]);
      showToast("Nova planilha gerada e pronta para baixar.");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setExporting(false);
    }
  }

  async function finishBankImport(result) {
    setBankModalOpen(false);
    if (result.export) {
      setExports((current) => [result.export, ...current]);
    }
    const skippedMessage = result.skipped_count
      ? ` ${result.skipped_count} duplicado(s) foram ignorados.`
      : "";
    const reconciledMessage = result.reconciled_count
      ? ` ${result.reconciled_count} valor(es) fixo(s) foram corrigidos no mês.`
      : "";
    const investmentsMessage = result.investments_imported_count
      ? ` ${result.investments_imported_count} investimento(s) foram adicionados na aba Investimentos.`
      : "";
    showToast(
      `${result.imported_count} gasto(s) importado(s).${investmentsMessage}${reconciledMessage}${skippedMessage}`,
      result.imported_count || result.investments_imported_count ? "success" : "error",
    );
    await loadAll();
  }

  function openNew(mode) {
    setNewEntryMode(mode);
    setModalEntry(undefined);
    setModalOpen(true);
  }

  function openEdit(entry) {
    setModalEntry(entry);
    setModalOpen(true);
  }

  return (
    <div className="app-shell">
      <aside className={mobileNav ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <span className="brand-mark"><OrcaIcon size={30} /></span>
          <div><strong>Orca</strong><small>finanças claras</small></div>
        </div>

        <nav>
          <span className="nav-label">Visão geral</span>
          <button
            className={tab === "dashboard" ? "active" : ""}
            onClick={() => { setTab("dashboard"); setMobileNav(false); }}
          >
            <LayoutDashboard size={19} /> Dashboard
          </button>
          <button
            className={tab === "editor" ? "active" : ""}
            onClick={() => { setTab("editor"); setMobileNav(false); }}
          >
            <ReceiptText size={19} /> Lançamentos
            <span>{entries.length}</span>
          </button>
          <button
            className={tab === "investments" ? "active" : ""}
            onClick={() => { setTab("investments"); setMobileNav(false); }}
          >
            <TrendingUp size={19} /> Investimentos
            <span>{investments.length}</span>
          </button>
        </nav>

        <div className="sidebar-note">
          <FileSpreadsheet size={19} />
          <strong>Planilha conectada</strong>
          <span>As alterações geram versões automaticamente.</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileNav((open) => !open)}
            aria-label="Abrir navegação"
          >
            <Menu size={21} />
          </button>
          <div>
            <span className="page-kicker">
              {tab === "dashboard"
                ? "Seu dinheiro, sem ruído"
                : tab === "investments"
                  ? "Patrimônio em separado"
                  : "Controle do banco de dados"}
            </span>
            <h1>
              {tab === "dashboard"
                ? "Resumo mensal"
                : tab === "investments"
                  ? "Investimentos"
                  : "Editar lançamentos"}
            </h1>
          </div>
          <div className="topbar-actions">
            <span className="signed-in-user">{auth.user.username}</span>
            <button className="secondary-button logout-button" onClick={logout}>
              <LogOut size={16} /> Sair
            </button>
            <label className="month-picker year-picker">
              <span>Ano</span>
              <div className="year-select">
                <select
                  aria-label="Selecionar ano"
                  value={month.slice(0, 4)}
                  onChange={(event) =>
                    setMonth(`${event.target.value}-${month.slice(5)}`)
                  }
                >
                  {YEARS.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
                <ChevronDown size={15} aria-hidden="true" />
              </div>
            </label>
            {tab === "dashboard" && (
              <div className="new-expense-actions">
                <button className="primary-button" onClick={() => openNew("fixed")}>
                  <Repeat2 size={16} /> Novo gasto fixo
                </button>
                <button className="secondary-button" onClick={() => openNew("monthly")}>
                  <Plus size={17} /> Gasto do mês
                </button>
              </div>
            )}
          </div>
        </header>

        <div className="content">
          {tab !== "investments" && <MonthTabs month={month} onChange={setMonth} />}
          {tab === "dashboard" ? (
            <>
              <Dashboard summary={summary} loading={loading} />
              <PlanSection plan={plan} />
            </>
          ) : tab === "investments" ? (
            <Investments
              investments={investments}
              loading={loading}
              onBankImport={() => setBankModalOpen(true)}
            />
          ) : (
            <Editor
              entries={entries}
              exports={exports}
              month={month}
              loading={loading}
              onAddFixed={() => openNew("fixed")}
              onAddMonthly={() => openNew("monthly")}
              onBankImport={() => setBankModalOpen(true)}
              onEdit={openEdit}
              onDelete={deleteEntry}
              onExport={exportNow}
              exporting={exporting}
            />
          )}
        </div>
      </main>

      {mobileNav && <button className="nav-backdrop" onClick={() => setMobileNav(false)} />}

      {modalOpen && (
        <EntryModal
          entry={modalEntry}
          month={month}
          mode={newEntryMode}
          onClose={() => setModalOpen(false)}
          onSave={saveEntry}
          saving={saving}
        />
      )}

      {bankModalOpen && (
        <BankImportModal
          month={month}
          onClose={() => setBankModalOpen(false)}
          onImported={finishBankImport}
          onError={(message) => showToast(message, "error")}
        />
      )}

      {toast && (
        <div className={`toast ${toast.kind}`}>
          {toast.kind === "error" ? <X size={18} /> : <Check size={18} />}
          {toast.message}
        </div>
      )}
    </div>
  );
}
