const HOME_MARKETS = [
  { id: 'kospi',  name: 'KOSPI',   ticker: '^KS11', color: '#0078d4' },
  { id: 'kosdaq', name: 'KOSDAQ',  ticker: '^KQ11', color: '#8b5cf6' },
  { id: 'nasdaq', name: 'NASDAQ',  ticker: '^IXIC', color: '#0f766e' },
  { id: 'sp500',  name: 'S&P 500', ticker: '^GSPC', color: '#d97706' },
];

const PERIODS = [['1mo', '1M'], ['3mo', '3M'], ['6mo', '6M'], ['1y', '1Y']];
const UPWARD_COLOR = '#e11d48';
const DOWNWARD_COLOR = '#2563eb';
const VOLUME_FALLBACK_COLOR = '#94a3b8';
const VOLUME_SERIES_INDEX = 2;

function chartCard(market) {
  return `
    <section class="home-market-card" data-market-card="${market.id}">
      <header class="home-market-card-head">
        <div>
          <div class="home-market-name">${market.name} <span>· ${market.ticker}</span></div>
          <div class="home-market-price-row">
            <strong data-price="${market.id}">--</strong>
            <em data-change="${market.id}">--</em>
          </div>
        </div>
        <div class="home-market-actions">
          <div class="home-market-periods" data-periods="${market.id}">
            ${PERIODS.map(([value, label]) => `<button type="button" data-period="${value}" class="${value === '3mo' ? 'active' : ''}">${label}</button>`).join('')}
          </div>
          <button type="button" class="home-market-expand" data-expand="${market.id}" aria-label="${market.name} 차트 크게 보기" aria-pressed="false">
            <i class="fa-solid fa-expand"></i><span>크게 보기</span>
          </button>
        </div>
      </header>
      <div class="home-market-chart-wrap">
        <div class="home-market-chart" data-chart="${market.id}"></div>
        <div class="home-market-loading" data-loading="${market.id}"><i class="fa-solid fa-spinner fa-spin"></i> 데이터 불러오는 중…</div>
      </div>
      <footer class="home-market-foot">
        <span><i class="fa-solid fa-chart-line"></i> 일봉 · MA20 · 거래량</span>
        <span data-simulated="${market.id}"></span>
      </footer>
    </section>`;
}

function todayISO(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

function boxRangeCard() {
  return `
    <section class="home-box-card" id="home-box-card">
      <header class="home-box-head">
        <div class="home-box-title"><i class="fa-solid fa-box-archive"></i> 박스권(지지·저항) 분석</div>
        <div class="home-box-controls">
          <select data-box-market>
            ${HOME_MARKETS.map((m) => `<option value="${m.id}">${m.name}</option>`).join('')}
          </select>
          <label>From <input type="date" data-box-start value="${todayISO(-90)}"></label>
          <label>To <input type="date" data-box-end value="${todayISO(0)}"></label>
          <button type="button" data-box-run><i class="fa-solid fa-magnifying-glass"></i> 조회</button>
        </div>
      </header>
      <p class="home-box-desc">선택한 기간(from~to) 안에서 가장 높았던 가격(박스 상단)과 가장 낮았던 가격(박스 하단)을 구하고, 현재가가 그 상단·하단까지 각각 몇 % 남았는지 보여줍니다.</p>
      <div class="home-box-body">
        <div class="home-box-chart-wrap">
          <div class="home-box-chart" data-box-chart></div>
          <div class="home-box-loading" data-box-loading><i class="fa-solid fa-spinner fa-spin"></i> 데이터 불러오는 중…</div>
        </div>
        <div class="home-box-stats" data-box-stats></div>
      </div>
    </section>`;
}

export function homeView(container, navigate) {
  container.innerHTML = `
    <div class="home-dashboard" id="home-dashboard">
      <div class="home-market-grid">${HOME_MARKETS.map(chartCard).join('')}</div>
      ${boxRangeCard()}
      <section class="home-quick-links">
        <button data-view="macro-realtime"><i class="fa-solid fa-satellite-dish"></i> 거시경제현황</button>
        <button data-view="industry-analysis"><i class="fa-solid fa-industry"></i> 산업 경쟁력 분석</button>
        <button data-view="dart-financial-analysis"><i class="fa-solid fa-file-invoice-dollar"></i> DART 재무 AI 분석</button>
        <button data-view="technical-chart"><i class="fa-solid fa-chart-candlestick"></i> 기술적 분석</button>
      </section>
    </div>`;

  container.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => navigate(button.dataset.view)));

  const charts = new Map();
  const periods = new Map(HOME_MARKETS.map((market) => [market.id, '3mo']));
  let expandedMarket = null;

  function destroyChart(id) {
    const chart = charts.get(id);
    if (chart) { try { chart.destroy(); } catch {} charts.delete(id); }
  }

  function chartHeight(id) {
    return expandedMarket === id ? 600 : 230;
  }

  async function loadChart(market) {
    const id = market.id;
    const card = container.querySelector(`[data-market-card="${id}"]`);
    const chartEl = card.querySelector(`[data-chart="${id}"]`);
    const loading = card.querySelector(`[data-loading="${id}"]`);
    const price = card.querySelector(`[data-price="${id}"]`);
    const change = card.querySelector(`[data-change="${id}"]`);
    const simulated = card.querySelector(`[data-simulated="${id}"]`);
    loading.style.display = 'flex';
    destroyChart(id);

    try {
      const res = await fetch(`/api/home/market-candle?market=${encodeURIComponent(id)}&period=${periods.get(id)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const ohlcv = data.ohlcv || [];
      if (!ohlcv.length) throw new Error('데이터 없음');
      const last = ohlcv.at(-1);
      const prev = ohlcv.length > 1 ? ohlcv.at(-2).c : last.o;
      const pct = ((last.c / prev) - 1) * 100;
      const up = pct >= 0;
      price.textContent = last.c.toLocaleString(undefined, { maximumFractionDigits: 2 });
      change.textContent = `${up ? '▲' : '▼'} ${Math.abs(pct).toFixed(2)}%`;
      change.className = up ? 'is-up' : 'is-down';
      simulated.textContent = data.is_simulated ? '시뮬레이션 데이터' : 'Yahoo Finance · 15분 지연';
      simulated.classList.toggle('is-simulated', Boolean(data.is_simulated));

      const candles = ohlcv.map((point) => ({ x: new Date(point.date).getTime(), y: [point.o, point.h, point.l, point.c] }));
      const ma20 = ohlcv.map((point, index) => ({
        x: new Date(point.date).getTime(),
        y: index < 19 ? null : ohlcv.slice(index - 19, index + 1).reduce((sum, item) => sum + item.c, 0) / 20,
      }));
      const volume = ohlcv.map((point) => ({
        x: new Date(point.date).getTime(),
        y: point.v || 0,
        fillColor: point.c >= point.o ? UPWARD_COLOR : DOWNWARD_COLOR,
      }));
      const chart = new ApexCharts(chartEl, {
        chart: { type: 'candlestick', height: chartHeight(id), toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: false }, background: '#fff', fontFamily: 'Pretendard, -apple-system, "Malgun Gothic", sans-serif' },
        series: [{ name: market.name, type: 'candlestick', data: candles }, { name: 'MA20', type: 'line', data: ma20 }, { name: '거래량', type: 'bar', data: volume }],
        plotOptions: { candlestick: { colors: { upward: UPWARD_COLOR, downward: DOWNWARD_COLOR }, wick: { useFillColor: true } }, bar: { columnWidth: '65%' } },
        // ApexCharts requires a color per series; individual volume bars override this neutral fallback by direction.
        colors: [UPWARD_COLOR, market.color, VOLUME_FALLBACK_COLOR], stroke: { curve: 'smooth', width: [1, 1.7, 0] },
        xaxis: { type: 'datetime', labels: { format: 'MM-dd', style: { fontSize: '10px', colors: '#94a3b8' }, hideOverlappingLabels: true, datetimeUTC: false }, axisBorder: { show: false }, axisTicks: { show: false } },
        yaxis: [
          { labels: { formatter: (value) => value ? Math.round(value).toLocaleString() : '', style: { fontSize: '10px', colors: '#94a3b8' } } },
          { show: false },
          { show: false, seriesName: '거래량' },
        ],
        grid: { borderColor: '#eef2f7', strokeDashArray: 3, padding: { right: 10, left: 4 } },
        tooltip: {
          shared: false,
          x: { format: 'yyyy-MM-dd' },
          y: {
            formatter: (value, { seriesIndex }) => {
              if (value == null) return '';
              return seriesIndex === VOLUME_SERIES_INDEX
                ? Math.round(value).toLocaleString()
                : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
            },
          },
        },
        legend: { show: false },
      });
      charts.set(id, chart);
      await chart.render();
      loading.style.display = 'none';
    } catch (error) {
      loading.innerHTML = `<span class="home-market-error">데이터 오류: ${error.message}</span>`;
    }
  }

  function setExpanded(id) {
    const previousMarket = expandedMarket;
    expandedMarket = id;
    const dashboard = container.querySelector('#home-dashboard');
    dashboard.classList.toggle('is-chart-expanded', Boolean(id));
    container.querySelectorAll('[data-market-card]').forEach((card) => card.classList.toggle('is-expanded', card.dataset.marketCard === id));
    HOME_MARKETS.forEach((market) => {
      const button = container.querySelector(`[data-expand="${market.id}"]`);
      const isExpanded = market.id === id;
      button.classList.toggle('is-collapse', isExpanded);
      button.setAttribute('aria-pressed', String(isExpanded));
      button.setAttribute('aria-label', `${market.name} 차트 ${isExpanded ? '작게 보기' : '크게 보기'}`);
      button.innerHTML = isExpanded
        ? '<i class="fa-solid fa-compress"></i><span>작게 보기</span>'
        : '<i class="fa-solid fa-expand"></i><span>크게 보기</span>';
    });
    if (id) loadChart(HOME_MARKETS.find((market) => market.id === id));
    else if (previousMarket) loadChart(HOME_MARKETS.find((market) => market.id === previousMarket));
  }

  HOME_MARKETS.forEach((market) => {
    container.querySelector(`[data-periods="${market.id}"]`).addEventListener('click', (event) => {
      const button = event.target.closest('[data-period]');
      if (!button) return;
      periods.set(market.id, button.dataset.period);
      container.querySelectorAll(`[data-periods="${market.id}"] [data-period]`).forEach((item) => item.classList.toggle('active', item === button));
      loadChart(market);
    });
    container.querySelector(`[data-expand="${market.id}"]`).addEventListener('click', () => setExpanded(expandedMarket === market.id ? null : market.id));
    loadChart(market);
  });

  // ── 박스권(지지·저항) 분석 ────────────────────────────────────────────────
  let boxChart = null;
  const boxCard    = container.querySelector('#home-box-card');
  const boxMarket   = boxCard.querySelector('[data-box-market]');
  const boxStart    = boxCard.querySelector('[data-box-start]');
  const boxEnd      = boxCard.querySelector('[data-box-end]');
  const boxChartEl  = boxCard.querySelector('[data-box-chart]');
  const boxLoading  = boxCard.querySelector('[data-box-loading]');
  const boxStatsEl  = boxCard.querySelector('[data-box-stats]');

  function destroyBoxChart() {
    if (boxChart) { try { boxChart.destroy(); } catch {} boxChart = null; }
  }

  function renderBoxStats(data) {
    const stats = [
      ['박스 상단(최고가)', `${data.box_high.toLocaleString()}`, '#e11d48'],
      ['현재가',            `${data.last_close.toLocaleString()}`, '#0f172a'],
      ['박스 하단(최저가)', `${data.box_low.toLocaleString()}`, '#2563eb'],
      ['상단까지 여력',      data.upper_pct != null ? `+${data.upper_pct}%` : '-', '#e11d48'],
      ['하단까지 여력',      data.lower_pct != null ? `-${data.lower_pct}%` : '-', '#2563eb'],
      ['박스권 내 위치',     data.position_pct != null ? `${data.position_pct}%` : '-', '#7c3aed'],
    ];
    boxStatsEl.innerHTML = stats.map(([label, value, color]) => `
      <div class="home-box-stat">
        <span class="home-box-stat-label">${label}</span>
        <strong class="home-box-stat-value" style="color:${color};">${value}</strong>
      </div>`).join('');
  }

  async function loadBoxRange() {
    const market = boxMarket.value;
    const start  = boxStart.value;
    const end    = boxEnd.value;
    boxLoading.style.display = 'flex';
    destroyBoxChart();
    try {
      const res = await fetch(`/api/home/box-range?market=${encodeURIComponent(market)}&start=${start}&end=${end}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const ohlcv = data.ohlcv || [];
      if (!ohlcv.length) throw new Error('데이터 없음');

      renderBoxStats(data);

      const candles = ohlcv.map((point) => ({ x: new Date(point.date).getTime(), y: [point.o, point.h, point.l, point.c] }));
      boxChart = new ApexCharts(boxChartEl, {
        chart: { type: 'candlestick', height: 300, toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: false }, background: '#fff', fontFamily: 'Pretendard, -apple-system, "Malgun Gothic", sans-serif' },
        series: [{ name: data.name, type: 'candlestick', data: candles }],
        plotOptions: { candlestick: { colors: { upward: '#e11d48', downward: '#2563eb' }, wick: { useFillColor: true } } },
        xaxis: { type: 'datetime', labels: { format: 'MM-dd', style: { fontSize: '10px', colors: '#94a3b8' }, hideOverlappingLabels: true, datetimeUTC: false }, axisBorder: { show: false }, axisTicks: { show: false } },
        yaxis: { labels: { formatter: (value) => value ? Math.round(value).toLocaleString() : '', style: { fontSize: '10px', colors: '#94a3b8' } } },
        grid: { borderColor: '#eef2f7', strokeDashArray: 3, padding: { right: 10, left: 4 } },
        annotations: { yaxis: [
          { y: data.box_high, borderColor: '#e11d48', strokeDashArray: 4, label: { text: `박스 상단 ${data.box_high.toLocaleString()}`, style: { background: '#e11d48', color: '#fff', fontSize: '10px' } } },
          { y: data.box_low,  borderColor: '#2563eb', strokeDashArray: 4, label: { text: `박스 하단 ${data.box_low.toLocaleString()}`, style: { background: '#2563eb', color: '#fff', fontSize: '10px' } } },
        ] },
        tooltip: { shared: false, x: { format: 'yyyy-MM-dd' } }, legend: { show: false },
      });
      await boxChart.render();
      boxLoading.style.display = 'none';
    } catch (error) {
      boxLoading.innerHTML = `<span class="home-market-error">데이터 오류: ${error.message}</span>`;
    }
  }

  boxCard.querySelector('[data-box-run]').addEventListener('click', loadBoxRange);
  loadBoxRange();

  window._viewCleanup = () => {
    charts.forEach((chart) => { try { chart.destroy(); } catch {} });
    destroyBoxChart();
  };
}
