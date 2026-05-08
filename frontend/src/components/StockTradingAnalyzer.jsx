import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart3, Plus, Trash2, AlertCircle, FileText, Activity, User, PieChart, Download, Bookmark, Trophy, Pencil, X } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceDot, PieChart as RechartsPie, Pie, Cell } from 'recharts';
import stockApi from '../api/stockApi';

const StockTradingAnalyzer = () => {
  const [currentPage, setCurrentPage] = useState('input');
  const [trades, setTrades] = useState([]);
  const [currentTrade, setCurrentTrade] = useState({
    stockName: '',
    tradeType: 'buy',
    date: '',
    price: '',
    quantity: ''
  });

  const [searchResults, setSearchResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');

  const [strategy, setStrategy] = useState('bollinger');
  const [externalUrl, setExternalUrl] = useState('');
  const [selectedStock, setSelectedStock] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savedStrategies, setSavedStrategies] = useState([]);
  const [strategySaveMsg, setStrategySaveMsg] = useState('');
  const [strategyName, setStrategyName] = useState('');

  const [editingTradeId, setEditingTradeId] = useState(null);
  const [chartSelectedStock, setChartSelectedStock] = useState('');
  const [stockData, setStockData] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState(null);
  const [currentPrices, setCurrentPrices] = useState({});
  const [mypagePricesLoading, setMypagePricesLoading] = useState(false);
  const [priceHistories, setPriceHistories] = useState({});
  const [portfolioTimelineLoading, setPortfolioTimelineLoading] = useState(false);
  const [indexPrices, setIndexPrices] = useState({ KOSPI: [], KOSDAQ: [] });

  const stockNamesKey = React.useMemo(
    () => [...new Set(trades.map(t => t.stockName))].sort().join(','),
    [trades]
  );

  const [performanceData, setPerformanceData] = useState([]);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [expandedItemId, setExpandedItemId] = useState(null);

  useEffect(() => {
    if (currentPage === 'ai-performance' || currentPage === 'mypage') {
      setPerformanceLoading(true);
      stockApi.getAiPerformance()
        .then(data => setPerformanceData(data))
        .catch(() => setPerformanceData([]))
        .finally(() => setPerformanceLoading(false));
    }
  }, [currentPage]);


  // 1. 컴포넌트 마운트 시 거래 내역 + 저장된 전략 불러오기
React.useEffect(() => {
  const loadTrades = async () => {
    try {
      const allTrades = await stockApi.getAllTrades();
      setTrades(allTrades);
    } catch (error) {
      console.error('거래 내역 로딩 실패:', error);
    }
  };

  const loadStrategies = async () => {
    try {
      const data = await stockApi.getSavedStrategies();
      setSavedStrategies(data);
    } catch (error) {
      console.error('전략 로딩 실패:', error);
    }
  };

  loadTrades();
  loadStrategies();
}, []);

// 차트 페이지 진입 시 기본 종목 설정
React.useEffect(() => {
  if (currentPage === 'chart' && trades.length > 0) {
    const unique = [...new Set(trades.map(t => t.stockName))];
    if (!unique.includes(chartSelectedStock)) {
      setChartSelectedStock(unique[0]);
    }
  }
}, [currentPage, trades, chartSelectedStock]);

// 2. 차트 페이지에서 주가 데이터 불러오기
React.useEffect(() => {
  const fetchData = async () => {
    if (currentPage === 'chart' && chartSelectedStock) {
      setChartLoading(true);
      setChartError(null);
      setStockData(null);

      try {
        const stockTrades = trades.filter(t => t.stockName === chartSelectedStock);
        const firstTradeDate = stockTrades.map(t => t.date).sort()[0];

        const response = await stockApi.getStockPrices(chartSelectedStock, null, firstTradeDate);

        const tradesByDate = {};
        stockTrades.forEach(t => {
          const d = typeof t.date === 'string' ? t.date : String(t.date);
          if (!tradesByDate[d]) tradesByDate[d] = [];
          tradesByDate[d].push(t);
        });

        const formattedData = response.prices.map(p => ({
          date: new Date(p.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
          fullDate: p.date,
          close: p.closePrice,
          trades: tradesByDate[p.date] || [],
        }));

        setStockData(formattedData);
      } catch (err) {
        console.error('주가 데이터 로딩 실패:', err);
        setChartError('주가 데이터를 불러오는데 실패했습니다.');
      } finally {
        setChartLoading(false);
      }
    }
  };

  fetchData();
}, [currentPage, chartSelectedStock, trades]);

// 3. 마이페이지 진입 시 주가 이력 조회 (현재가 + 타임라인용)
React.useEffect(() => {
  const fetchMyPageData = async () => {
    if (currentPage !== 'mypage' || trades.length === 0) return;

    const heldStocks = {};
    trades.forEach(t => {
      if (!heldStocks[t.stockName]) heldStocks[t.stockName] = { buy: 0, sell: 0 };
      if (t.tradeType === 'buy') heldStocks[t.stockName].buy += parseInt(t.quantity, 10);
      else heldStocks[t.stockName].sell += parseInt(t.quantity, 10);
    });

    const allStocks = [...new Set(trades.map(t => t.stockName))];
    const firstTradeDate = [...trades].sort((a, b) => new Date(a.date) - new Date(b.date))[0]?.date;

    setMypagePricesLoading(true);
    setPortfolioTimelineLoading(true);
    try {
      const results = await Promise.all(
        allStocks.map(name =>
          stockApi.getStockPrices(name, null, firstTradeDate).then(res => ({
            name,
            prices: res.prices || []
          })).catch(() => ({ name, prices: [] }))
        )
      );
      const priceMap = {};
      const historyMap = {};
      results.forEach(({ name, prices }) => {
        historyMap[name] = prices;
        const isHeld = (heldStocks[name]?.buy || 0) - (heldStocks[name]?.sell || 0) > 0;
        if (isHeld && prices.length > 0) {
          priceMap[name] = prices[prices.length - 1].closePrice;
        }
      });
      setCurrentPrices(priceMap);
      setPriceHistories(historyMap);

      const [kospiData, kosdaqData] = await Promise.all([
        stockApi.getIndexPrices('KOSPI', firstTradeDate),
        stockApi.getIndexPrices('KOSDAQ', firstTradeDate),
      ]);
      setIndexPrices({ KOSPI: kospiData, KOSDAQ: kosdaqData });
    } catch (error) {
      console.error('마이페이지 가격 조회 실패:', error);
    } finally {
      setMypagePricesLoading(false);
      setPortfolioTimelineLoading(false);
    }
  };

  fetchMyPageData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [currentPage, stockNamesKey]);

  // 거래 목록 변경 시 종목 자동 선택 (단일 종목이면 바로 선택)
  React.useEffect(() => {
    const unique = [...new Set(trades.map(t => t.stockName))];
    if (unique.length === 1) {
      setSelectedStock(unique[0]);
    } else {
      setSelectedStock(prev => unique.includes(prev) ? prev : '');
    }
  }, [trades]);

  const portfolioTimeline = React.useMemo(() => {
    const stockNames = Object.keys(priceHistories);
    if (stockNames.length === 0) return [];

    const allDatesSet = new Set();
    stockNames.forEach(name => {
      (priceHistories[name] || []).forEach(p => allDatesSet.add(p.date));
    });
    const sortedDates = [...allDatesSet].sort();

    const priceLookup = {};
    stockNames.forEach(name => {
      priceLookup[name] = {};
      let lastPrice = null;
      sortedDates.forEach(date => {
        const entry = (priceHistories[name] || []).find(p => p.date === date);
        if (entry) lastPrice = parseFloat(entry.closePrice);
        if (lastPrice != null) priceLookup[name][date] = lastPrice;
      });
    });

    // 지수 forward-fill lookup 생성
    const buildIndexLookup = (data) => {
      const lookup = {};
      let last = null;
      sortedDates.forEach(date => {
        const entry = data.find(p => p.date === date);
        if (entry) last = parseFloat(entry.closePrice);
        if (last != null) lookup[date] = last;
      });
      return lookup;
    };
    const kospiLookup = buildIndexLookup(indexPrices.KOSPI);
    const kosdaqLookup = buildIndexLookup(indexPrices.KOSDAQ);

    const sortedTrades = [...trades].sort((a, b) => new Date(a.date) - new Date(b.date));
    const firstTradeDate = sortedTrades[0]?.date;
    if (!firstTradeDate) return [];

    const filtered = sortedDates
      .filter(date => date >= firstTradeDate)
      .map(date => {
        const holdingsOnDate = {};
        sortedTrades.forEach(t => {
          if (t.date <= date) {
            const name = t.stockName;
            if (!holdingsOnDate[name]) holdingsOnDate[name] = 0;
            holdingsOnDate[name] += t.tradeType === 'buy'
              ? (parseInt(t.quantity, 10) || 0)
              : -(parseInt(t.quantity, 10) || 0);
          }
        });

        let totalValue = 0;
        stockNames.forEach(name => {
          const qty = Math.max(0, holdingsOnDate[name] || 0);
          const price = priceLookup[name][date];
          if (qty > 0 && price) totalValue += qty * price;
        });

        // 해당 날짜까지 누적 매수금액 + 이동평균법 실현손익
        let totalBought = 0;
        let cumulativeRealizedPL = 0;
        const runningAvg = {};
        sortedTrades.forEach(t => {
          if (t.date > date) return;
          const name = t.stockName;
          const qty = parseInt(t.quantity, 10) || 0;
          const price = parseFloat(t.price) || 0;
          if (!runningAvg[name]) runningAvg[name] = { qty: 0, amount: 0 };
          if (t.tradeType === 'buy') {
            totalBought += price * qty;
            runningAvg[name].qty += qty;
            runningAvg[name].amount += price * qty;
          } else {
            const avgPrice = runningAvg[name].qty > 0 ? runningAvg[name].amount / runningAvg[name].qty : 0;
            cumulativeRealizedPL += (price - avgPrice) * qty;
            runningAvg[name].qty -= qty;
            runningAvg[name].amount = runningAvg[name].qty > 0 ? avgPrice * runningAvg[name].qty : 0;
          }
        });

        return {
          date,
          displayDate: new Date(date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
          totalValue: Math.round(totalValue),
          totalBought,
          cumulativeRealizedPL,
          kospi: kospiLookup[date] ?? null,
          kosdaq: kosdaqLookup[date] ?? null,
        };
      })
      .filter(d => d.totalValue > 0);

    if (filtered.length === 0) return [];

    const baseKospi  = filtered[0].kospi;
    const baseKosdaq = filtered[0].kosdaq;
    const basePortfolioReturn = filtered[0].totalBought > 0
      ? (filtered[0].totalValue + filtered[0].cumulativeRealizedPL - filtered[0].totalBought) / filtered[0].totalBought * 100
      : 0;

    return filtered.map(d => ({
      ...d,
      portfolioReturn: d.totalBought > 0
        ? parseFloat(((d.totalValue + d.cumulativeRealizedPL - d.totalBought) / d.totalBought * 100 - basePortfolioReturn).toFixed(2))
        : 0,
      kospiReturn:  baseKospi  && d.kospi  ? parseFloat(((d.kospi  - baseKospi)  / baseKospi  * 100).toFixed(2)) : null,
      kosdaqReturn: baseKosdaq && d.kosdaq ? parseFloat(((d.kosdaq - baseKosdaq) / baseKosdaq * 100).toFixed(2)) : null,
    }));
  }, [priceHistories, trades, indexPrices]);

  useEffect(() => {
    if (searchKeyword.length === 0) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const results = await stockApi.searchStocks(searchKeyword);
        setSearchResults(results);
        setShowDropdown(true);
      } catch (error) {
        setSearchResults([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchKeyword]);

  const handleStockNameChange = (value) => {
    setCurrentTrade({...currentTrade, stockName: value});
    setSearchKeyword(value);
  };

  const selectStock = (stockName) => {
    setCurrentTrade({...currentTrade, stockName});
    setShowDropdown(false);
    setSearchResults([]);
  };


  const resetTradeForm = () => {
    setCurrentTrade({ stockName: '', tradeType: 'buy', date: '', price: '', quantity: '' });
    setEditingTradeId(null);
  };

  const addTrade = async () => {
    if (!currentTrade.stockName || !currentTrade.date || !currentTrade.price || !currentTrade.quantity) return;

    if (editingTradeId) {
      try {
        const response = await stockApi.updateTrade(editingTradeId, currentTrade);
        setTrades(trades.map(t => t.id === editingTradeId ? response : t));
        resetTradeForm();
      } catch (error) {
        console.error('거래 수정 실패:', error);
        alert('거래 수정에 실패했습니다.');
      }
      return;
    }

    if (currentTrade.tradeType === 'sell') {
      const heldQty = trades
        .filter(t => t.stockName === currentTrade.stockName)
        .reduce((sum, t) => sum + (t.tradeType === 'buy' ? 1 : -1) * (parseInt(t.quantity, 10) || 0), 0);
      if ((parseInt(currentTrade.quantity, 10) || 0) > heldQty) {
        alert(`보유 수량(${heldQty}주)을 초과하여 매도할 수 없습니다.`);
        return;
      }
    }
    try {
      const response = await stockApi.createTrade(currentTrade);
      setTrades([...trades, response]);
      resetTradeForm();
    } catch (error) {
      console.error('거래 추가 실패:', error);
      alert('거래 추가에 실패했습니다.');
    }
  };

  const removeTrade = async (id) => {
  try {
    await stockApi.deleteTrade(id);
    setTrades(trades.filter(trade => trade.id !== id));
  } catch (error) {
    console.error('거래 삭제 실패:', error);
    alert('거래 삭제에 실패했습니다.');
  }
};

  const removeAllTrades = async () => {
  if (!window.confirm('전체 거래 내역을 삭제하시겠습니까?')) return;
  try {
    await stockApi.deleteAllTrades();
    setTrades([]);
  } catch (error) {
    console.error('전체 거래 삭제 실패:', error);
    alert('전체 거래 삭제에 실패했습니다.');
  }
};

  const analyzeTrading = async () => {
  if (trades.length === 0) {
    alert('거래 내역을 먼저 입력해주세요.');
    return;
  }

  if (strategy === 'external' && !externalUrl) {
    alert('외부 전략 URL을 입력해주세요.');
    return;
  }

  if (!selectedStock) {
    alert('분석할 종목을 선택해주세요.');
    return;
  }

  setLoading(true);

  try {
    const response = await stockApi.analyzeTrading(strategy, externalUrl, selectedStock);
    
    setAnalysis(response);
    setCurrentPage('analysis');
  } catch (error) {
    console.error('AI 분석 실패:', error);
    alert('AI 분석에 실패했습니다. 다시 시도해주세요.');
  } finally {
    setLoading(false);
  }
};  



  const saveStrategy = async () => {
    if (strategy !== 'external' || !externalUrl) return;
    if (savedStrategies.some(s => s.url === externalUrl)) {
      setStrategySaveMsg('already');
      setTimeout(() => setStrategySaveMsg(''), 2500);
      return;
    }
    try {
      const saved = await stockApi.saveStrategy(externalUrl, strategyName || null);
      setSavedStrategies([saved, ...savedStrategies]);
      setStrategySaveMsg('ok');
      setStrategyName('');
      setTimeout(() => setStrategySaveMsg(''), 2500);
    } catch (error) {
      console.error('전략 저장 실패:', error);
      setStrategySaveMsg('already');
      setTimeout(() => setStrategySaveMsg(''), 2500);
    }
  };

  const removeSavedStrategy = async (id) => {
    try {
      await stockApi.deleteStrategy(id);
      setSavedStrategies(savedStrategies.filter(s => s.id !== id));
    } catch (error) {
      console.error('전략 삭제 실패:', error);
    }
  };

  const downloadCSV = () => {
    const escapeCSV = (value) => {
      const str = String(value);
      if (/^[=+\-@\t\r]/.test(str)) return `"'${str.replace(/"/g, '""')}"`;
      if (str.includes(',') || str.includes('"') || str.includes('\n')) return `"${str.replace(/"/g, '""')}"`;
      return str;
    };
    const header = '종목명,거래구분,날짜,가격(원),수량(주),거래금액(원)';
    const rows = trades.map(t => {
      const price = parseFloat(t.price) || 0;
      const qty = parseInt(t.quantity, 10) || 0;
      return [
        escapeCSV(t.stockName),
        escapeCSV(t.tradeType === 'buy' ? '매수' : '매도'),
        escapeCSV(t.date),
        escapeCSV(price),
        escapeCSV(qty),
        escapeCSV(Math.round(price * qty))
      ].join(',');
    });
    const csv = [header, ...rows].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `inveskit_trades_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadPDF = () => {
    window.print();
  };

  const renderInputPage = () => (
    <div className="max-w-6xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              {editingTradeId ? <Pencil className="w-5 h-5 text-blue-600" /> : <Plus className="w-5 h-5" />}
              {editingTradeId ? '거래 수정' : '매매 기록 입력'}
            </h2>
            {editingTradeId && (
              <div className="mb-3 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700 flex items-center justify-between">
                <span>수정 중입니다. 변경사항을 저장하거나 취소하세요.</span>
                <button onClick={resetTradeForm} className="ml-2 text-blue-500 hover:text-blue-700"><X className="w-3.5 h-3.5" /></button>
              </div>
            )}
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">종목명</label>
                <div className="relative">
                <input
                  type="text"
                  value={currentTrade.stockName}
                  onChange={(e) => handleStockNameChange(e.target.value)}
                  onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
                  placeholder="예: 삼성전자"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                />

                {/* 자동완성 드롭다운 */}
                {showDropdown && searchResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {searchResults.map((stock, index) => (
                      <div
                        key={index}
                        onClick={() => selectStock(stock)}
                        className="px-4 py-2 hover:bg-slate-100 cursor-pointer transition-colors"
                      >
                        {stock}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
                          
            <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">거래 구분</label>
                  <select
                    value={currentTrade.tradeType}
                    onChange={(e) => setCurrentTrade({...currentTrade, tradeType: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                  >
                    <option value="buy">매수</option>
                    <option value="sell">매도</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">거래일</label>
                  <input
                    type="date"
                    value={currentTrade.date}
                    onChange={(e) => setCurrentTrade({...currentTrade, date: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">가격 (원)</label>
                  <input
                    type="number"
                    value={currentTrade.price}
                    onChange={(e) => setCurrentTrade({...currentTrade, price: e.target.value})}
                    placeholder="70000"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">수량 (주)</label>
                  <input
                    type="number"
                    value={currentTrade.quantity}
                    onChange={(e) => setCurrentTrade({...currentTrade, quantity: e.target.value})}
                    placeholder="10"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={addTrade}
                  className="flex-1 bg-slate-900 text-white py-2.5 rounded-lg font-medium hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
                >
                  {editingTradeId ? <><Pencil className="w-4 h-4" />수정 저장</> : <><Plus className="w-4 h-4" />거래 추가</>}
                </button>
                {editingTradeId && (
                  <button
                    onClick={resetTradeForm}
                    className="px-4 py-2.5 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors text-sm font-medium"
                  >
                    취소
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              분석 전략 선택
            </h2>

            {/* 종목 선택 (복수 종목인 경우에만 표시) */}
            {[...new Set(trades.map(t => t.stockName))].length > 1 && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <label className="block text-sm font-medium text-blue-900 mb-2">
                  분석할 종목 선택
                </label>
                <select
                  value={selectedStock}
                  onChange={(e) => setSelectedStock(e.target.value)}
                  className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                >
                  <option value="">종목을 선택하세요</option>
                  {[...new Set(trades.map(t => t.stockName))].map(name => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
                <p className="text-xs text-blue-700 mt-1.5">
                  AI는 선택한 종목의 거래 내역만 분석합니다
                </p>
              </div>
            )}
            
            <div className="space-y-3">
              <label className="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-colors">
                <input
                  type="radio"
                  name="strategy"
                  value="bollinger"
                  checked={strategy === 'bollinger'}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-4 h-4 text-slate-900"
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">볼린저 밴드</div>
                  <div className="text-sm text-gray-500">변동성 기반 매매 타이밍 분석</div>
                </div>
              </label>

              <label className="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-colors">
                <input
                  type="radio"
                  name="strategy"
                  value="trend"
                  checked={strategy === 'trend'}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-4 h-4 text-slate-900"
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">추세추종</div>
                  <div className="text-sm text-gray-500">이동평균선 기반 추세 분석</div>
                </div>
              </label>

              <label className="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-colors">
                <input
                  type="radio"
                  name="strategy"
                  value="external"
                  checked={strategy === 'external'}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-4 h-4 text-slate-900"
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">외부 전략</div>
                  <div className="text-sm text-gray-500">유튜브 등 외부 전략 콘텐츠 기반 분석</div>
                </div>
              </label>
            </div>

            {strategy === 'external' && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
                {savedStrategies.length > 0 && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">저장된 전략 선택</label>
                    <div className="space-y-1">
                      {savedStrategies.map(s => (
                        <button
                          key={s.id}
                          onClick={() => setExternalUrl(s.url)}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition-colors ${
                            externalUrl === s.url
                              ? 'bg-slate-900 text-white border-slate-900'
                              : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-100'
                          }`}
                        >
                          <span className="font-medium">{s.name || '이름 없음'}</span>
                          <span className={`text-xs ml-2 truncate ${externalUrl === s.url ? 'opacity-60' : 'text-gray-400'}`}>{s.url}</span>
                        </button>
                      ))}
                    </div>
                    <div className="flex items-center gap-2 my-3">
                      <div className="flex-1 h-px bg-gray-200" />
                      <span className="text-xs text-gray-400">또는</span>
                      <div className="flex-1 h-px bg-gray-200" />
                    </div>
                  </div>
                )}
                <label className="block text-sm font-medium text-gray-700 mb-2">새 URL 직접 입력</label>
                <input
                  type="url"
                  value={externalUrl}
                  onChange={(e) => setExternalUrl(e.target.value)}
                  placeholder="예: https://youtube.com/watch?v=..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                />
                <input
                  type="text"
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  placeholder="전략 명칭 (예: 볼린저밴드 실전편)"
                  className="w-full mt-2 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-2">
                  💡 유튜브, 블로그 등 투자 전략이 담긴 콘텐츠 URL을 입력하세요
                </p>
                <button
                  onClick={saveStrategy}
                  disabled={!externalUrl}
                  className="w-full mt-3 bg-slate-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-slate-600 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  전략 저장하기
                </button>
                {strategySaveMsg === 'ok' && (
                  <p className="text-xs text-emerald-600 mt-2 text-center">✓ 저장되었습니다</p>
                )}
                {strategySaveMsg === 'already' && (
                  <p className="text-xs text-amber-600 mt-2 text-center">이미 저장된 URL입니다</p>
                )}
              </div>
            )}

            <button
              onClick={analyzeTrading}
              disabled={trades.length === 0 || loading || (strategy === 'external' && !externalUrl) || !selectedStock}
              className="w-full mt-4 bg-emerald-600 text-white py-2.5 rounded-lg font-medium hover:bg-emerald-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? '분석 중...' : 'AI 분석 시작'}
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">입력된 거래 내역</h2>
              {trades.length > 0 && (
                <button
                  onClick={removeAllTrades}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  전체 삭제
                </button>
              )}
            </div>

            {trades.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <AlertCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">거래 내역이 없습니다</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {trades.map((trade) => (
                  <div key={trade.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{trade.stockName}</div>
                      <div className="text-sm text-gray-500">
                        {trade.date} | {trade.tradeType === 'buy' ? '매수' : '매도'} |
                        {parseInt(trade.price).toLocaleString()}원 × {trade.quantity}주
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => {
                          setCurrentTrade({
                            stockName: trade.stockName,
                            tradeType: trade.tradeType,
                            date: typeof trade.date === 'string' ? trade.date : String(trade.date),
                            price: trade.price,
                            quantity: trade.quantity,
                          });
                          setEditingTradeId(trade.id);
                        }}
                        className="text-blue-400 hover:text-blue-600 p-2"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => removeTrade(trade.id)}
                        className="text-red-500 hover:text-red-700 p-2"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  const ChartTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm min-w-[160px]">
        <p className="font-medium text-gray-700 mb-1">{d.date}</p>
        <p className="text-gray-600">종가: {Number(d.close).toLocaleString()}원</p>
        {d.trades?.length > 0 && (
          <div className="mt-2 border-t border-gray-100 pt-2 space-y-1">
            {d.trades.map((t, i) => (
              <p key={i} className={t.tradeType === 'buy' ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>
                {t.tradeType === 'buy' ? '▲ 매수' : '▼ 매도'} {Number(t.price).toLocaleString()}원 × {t.quantity}주
              </p>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderChartPage = () => {
    const uniqueStocks = [...new Set(trades.map(t => t.stockName))];
    const activeStock = chartSelectedStock || uniqueStocks[0] || null;
    const stockTrades = trades.filter(t => t.stockName === activeStock);

    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            주가 차트
          </h2>

          {uniqueStocks.length > 1 && (
            <div className="flex gap-2 mb-6 flex-wrap">
              {uniqueStocks.map(name => (
                <button
                  key={name}
                  onClick={() => setChartSelectedStock(name)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                    activeStock === name
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-slate-500'
                  }`}
                >
                  {name}
                </button>
              ))}
            </div>
          )}

          {trades.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <AlertCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-base">거래 내역을 먼저 입력해주세요</p>
            </div>
          ) : chartLoading ? (
            <div className="text-center py-16">
              <div className="text-gray-500">차트 로딩 중...</div>
            </div>
          ) : chartError ? (
            <div className="text-center py-16 text-red-500">
              <AlertCircle className="w-16 h-16 mx-auto mb-4" />
              <p className="text-base">{chartError}</p>
            </div>
          ) : stockData ? (
            <>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={stockData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                    tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="close"
                    stroke="#0f172a"
                    strokeWidth={2}
                    name="종가"
                    dot={false}
                  />
                  {stockTrades.map((trade) => {
                    const matchingData = stockData.find(d => d.fullDate === trade.date);
                    if (matchingData) {
                      return (
                        <ReferenceDot
                          key={trade.id}
                          x={matchingData.date}
                          y={parseFloat(trade.price)}
                          r={7}
                          fill={trade.tradeType === 'buy' ? '#10b981' : '#ef4444'}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      );
                    }
                    return null;
                  })}
                </LineChart>
              </ResponsiveContainer>

              <div className="flex gap-6 mt-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
                  <span className="text-gray-600">매수</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="text-gray-600">매도</span>
                </div>
              </div>

            </>
          ) : null}
        </div>
      </div>
    );
  };

  const SCORE_CRITERIA = [
    { label: '매수 타점', desc: '눌림목/지지선에서 매수했는가' },
    { label: '기술적 지표 활용', desc: '이동평균 등 지표 기반 매매인가' },
    { label: '추세 파악 능력', desc: '상승/하락 추세를 인식하고 대응했는가' },
    { label: '리스크 관리', desc: '손절 기준이 있는가, 과도한 추가 매수는 없는가' },
    { label: '전략 준수도', desc: 'YouTube 전략을 얼마나 따랐는가' },
  ];
  const GRADE_CRITERIA = [
    { range: '90 ~ 100점', label: '완벽한 전략 실행', color: 'text-emerald-600' },
    { range: '75 ~ 89점',  label: '대체로 우수',      color: 'text-blue-600'    },
    { range: '60 ~ 74점',  label: '핵심은 이해했으나 개선 필요', color: 'text-sky-600' },
    { range: '40 ~ 59점',  label: '전략과 괴리',       color: 'text-yellow-600'  },
    { range: '0 ~ 39점',   label: '무계획적 매매',     color: 'text-red-600'     },
  ];
  const AI_SIGNAL_LABEL = { buy: '매수 추천', sell: '매도 추천', hold: '보유 관망' };
  const AI_SIGNAL_STYLE = {
    buy:  'bg-emerald-100 text-emerald-800 border border-emerald-200',
    sell: 'bg-red-100 text-red-800 border border-red-200',
    hold: 'bg-blue-100 text-blue-800 border border-blue-200',
  };

  const renderAnalysisPage = () => (
  <div className="max-w-4xl mx-auto">
    {/* 점수 기준 모달 */}
    {showScoreModal && (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        onClick={() => setShowScoreModal(false)}
      >
        <div
          className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4"
          onClick={e => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-bold text-gray-900">종합 점수 채점 기준</h3>
            <button onClick={() => setShowScoreModal(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
          </div>

          <p className="text-xs text-gray-500 mb-3">각 항목 0~20점 × 5개 = 100점 만점</p>

          <div className="space-y-2 mb-5">
            {SCORE_CRITERIA.map((c, i) => (
              <div key={i} className="flex gap-3 p-2.5 bg-gray-50 rounded-lg">
                <span className="w-5 h-5 flex-shrink-0 bg-slate-900 text-white rounded-full text-xs flex items-center justify-center font-bold">{i + 1}</span>
                <div>
                  <div className="text-sm font-medium text-gray-800">{c.label}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{c.desc}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs font-semibold text-gray-700 mb-2">등급 기준</p>
            <div className="space-y-1">
              {GRADE_CRITERIA.map((g, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-gray-500 w-24">{g.range}</span>
                  <span className={`font-medium ${g.color}`}>{g.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )}

    {analysis ? (
      <div className="space-y-6">
        {/* 총점 카드 */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">AI 분석 결과</h2>
              <p className="text-sm text-gray-500">
                선택한 전략: <span className="font-medium text-gray-700">
                  {strategy === 'bollinger' ? '볼린저 밴드' :
                   strategy === 'trend' ? '추세추종' : '외부 전략'}
                </span>
              </p>
              {strategy === 'external' && externalUrl && (
                <a
                  href={externalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-800 mt-1 block break-all"
                >
                  🔗 {externalUrl}
                </a>
              )}
              {analysis.signal && (
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-xs text-gray-500">AI 추천 신호</span>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${AI_SIGNAL_STYLE[analysis.signal] || 'bg-gray-100 text-gray-700'}`}>
                    {AI_SIGNAL_LABEL[analysis.signal] || analysis.signal}
                  </span>
                </div>
              )}
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 mb-1">
                <span className="text-sm text-gray-500">종합 점수</span>
                <button
                  onClick={() => setShowScoreModal(true)}
                  className="w-4 h-4 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 text-xs flex items-center justify-center leading-none transition-colors"
                  title="채점 기준 보기"
                >
                  ?
                </button>
              </div>
              <div className={`text-4xl font-bold ${
                analysis.total_score >= 80 ? 'text-emerald-600' :
                analysis.total_score >= 60 ? 'text-blue-600' :
                analysis.total_score >= 40 ? 'text-yellow-600' :
                'text-red-600'
              }`}>
                {analysis.total_score}
                <span className="text-2xl text-gray-400">/100</span>
              </div>
            </div>
          </div>
        </div>

        {/* 거래별 분석 */}
        <div className="space-y-4">
          {analysis.analysis && analysis.analysis.map((item, index) => (
            <div key={index} className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-start gap-4">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${
                  index === 0 ? 'bg-yellow-500' :
                  index === 1 ? 'bg-gray-400' :
                  index === 2 ? 'bg-orange-400' :
                  'bg-slate-400'
                }`}>
                  {index + 1}
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <h3 className="text-lg font-semibold text-gray-900">{item.stockName}</h3>
                    <span className="px-2.5 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full">
                      {item.type === 'buy' ? '매수 거래' : item.type === 'sell' ? '매도 거래' : item.type}
                    </span>
                    {item.signal && (
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${AI_SIGNAL_STYLE[item.signal] || 'bg-gray-100 text-gray-700'}`}>
                        {AI_SIGNAL_LABEL[item.signal] || item.signal}
                      </span>
                    )}
                  </div>

                  {/* AI 조언 */}
                  <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
                    <div className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
                      <span>💡</span>
                      <span>AI 투자 조언</span>
                    </div>
                    <div className="text-sm text-blue-800 leading-relaxed whitespace-pre-wrap">
                      {item.advice}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 요약 통계 */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">분석 요약</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="text-xs text-gray-500 mb-1">분석된 거래</div>
              <div className="text-xl font-bold text-gray-900">
                {analysis.analysis ? analysis.analysis.length : 0}건
              </div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="text-xs text-gray-500 mb-1">종합 점수</div>
              <div className="text-xl font-bold text-gray-900">{analysis.total_score}점</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="text-xs text-gray-500 mb-1">평가 등급</div>
              <div className={`text-xl font-bold ${
                analysis.total_score >= 80 ? 'text-emerald-600' :
                analysis.total_score >= 60 ? 'text-blue-600' :
                analysis.total_score >= 40 ? 'text-yellow-600' :
                'text-red-600'
              }`}>
                {analysis.total_score >= 80 ? 'A' :
                 analysis.total_score >= 60 ? 'B' :
                 analysis.total_score >= 40 ? 'C' : 'D'}
              </div>
            </div>
          </div>
        </div>
      </div>
    ) : (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="text-center py-16 text-gray-400">
          <AlertCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-base">분석 결과가 없습니다</p>
          <p className="text-sm mt-2">거래 입력 페이지에서 AI 분석을 실행해주세요</p>
        </div>
      </div>
    )}
  </div>
);


  const renderMyPage = () => {
    // 날짜 순 정렬 후 이동평균법으로 실현 손익 계산 (매도 시점의 정확한 평균단가 반영)
    const sortedTrades = [...trades].sort((a, b) => new Date(a.date) - new Date(b.date));
    const runningAvg = {};
    let realizedProfitLoss = 0;

    sortedTrades.forEach(t => {
      const name = t.stockName;
      if (!runningAvg[name]) runningAvg[name] = { qty: 0, amount: 0 };
      const qty = parseInt(t.quantity, 10) || 0;
      const price = parseFloat(t.price) || 0;
      if (t.tradeType === 'buy') {
        runningAvg[name].qty += qty;
        runningAvg[name].amount += price * qty;
      } else {
        const avgPrice = runningAvg[name].qty > 0 ? runningAvg[name].amount / runningAvg[name].qty : 0;
        realizedProfitLoss += (price - avgPrice) * qty;
        runningAvg[name].qty -= qty;
        runningAvg[name].amount = runningAvg[name].qty > 0 ? avgPrice * runningAvg[name].qty : 0;
      }
    });

    // 종목별 집계 (UI 표시용)
    const holdingsByStock = {};
    trades.forEach(t => {
      const name = t.stockName;
      if (!holdingsByStock[name]) {
        holdingsByStock[name] = { totalBuyQty: 0, totalBuyAmount: 0, totalSellQty: 0, buyCount: 0, sellCount: 0 };
      }
      const qty = parseInt(t.quantity, 10) || 0;
      const price = parseFloat(t.price) || 0;
      if (t.tradeType === 'buy') {
        holdingsByStock[name].totalBuyQty += qty;
        holdingsByStock[name].totalBuyAmount += price * qty;
        holdingsByStock[name].buyCount++;
      } else {
        holdingsByStock[name].totalSellQty += qty;
        holdingsByStock[name].sellCount++;
      }
    });

    Object.keys(holdingsByStock).forEach(name => {
      const s = holdingsByStock[name];
      // 현재 보유분 평균단가는 이동평균 기준
      s.avgBuyPrice = runningAvg[name]?.qty > 0
        ? Math.round(runningAvg[name].amount / runningAvg[name].qty)
        : (s.totalBuyQty > 0 ? Math.round(s.totalBuyAmount / s.totalBuyQty) : 0);
      s.holdingQty = s.totalBuyQty - s.totalSellQty;
    });

    // 미실현 손익: 보유 수량 × (현재가 - 평균매수가)
    const unrealizedProfitLoss = Object.entries(holdingsByStock).reduce((sum, [name, s]) => {
      if (s.holdingQty <= 0) return sum;
      const curPrice = Number(currentPrices[name]) || null;
      if (!curPrice || curPrice <= 0) return sum;
      return sum + (curPrice - s.avgBuyPrice) * s.holdingQty;
    }, 0);

    const totalInvestment = Object.values(holdingsByStock).reduce((sum, s) => sum + s.totalBuyAmount, 0);
    const totalProfitLoss = Math.round(realizedProfitLoss + unrealizedProfitLoss);
    const profitRate = totalInvestment > 0 ? ((totalProfitLoss / totalInvestment) * 100).toFixed(2) : '0.00';

    const stockStats = holdingsByStock;

    const topStocks = Object.entries(stockStats)
      .sort((a, b) => (b[1].buyCount + b[1].sellCount) - (a[1].buyCount + a[1].sellCount))
      .slice(0, 5);

    const pieData = Object.entries(holdingsByStock).map(([name, s]) => ({
      name,
      value: s.totalBuyAmount
    }));

    const COLORS = ['#0f172a', '#334155', '#64748b', '#94a3b8', '#cbd5e1'];

    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900">마이페이지</h2>
          <p className="text-gray-500 text-sm mt-1">나의 투자 현황과 통계를 확인하세요</p>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <PieChart className="w-5 h-5" />
              투자 대시보드
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                <div className="text-sm text-slate-600 mb-1">총 투자금액</div>
                <div className="text-2xl font-bold text-slate-900">
                  {totalInvestment.toLocaleString()}원
                </div>
              </div>

              <div className={`p-4 rounded-lg border ${Math.round(realizedProfitLoss) >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <div className={`text-sm mb-1 ${Math.round(realizedProfitLoss) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>실현 손익</div>
                <div className={`text-2xl font-bold ${Math.round(realizedProfitLoss) >= 0 ? 'text-emerald-900' : 'text-red-900'}`}>
                  {Math.round(realizedProfitLoss) >= 0 ? '+' : ''}{Math.round(realizedProfitLoss).toLocaleString()}원
                </div>
              </div>

              <div className={`p-4 rounded-lg border ${mypagePricesLoading ? 'bg-gray-50 border-gray-200' : Math.round(unrealizedProfitLoss) >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <div className={`text-sm mb-1 ${mypagePricesLoading ? 'text-gray-500' : Math.round(unrealizedProfitLoss) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>미실현 손익</div>
                <div className={`text-2xl font-bold ${mypagePricesLoading ? 'text-gray-400' : Math.round(unrealizedProfitLoss) >= 0 ? 'text-emerald-900' : 'text-red-900'}`}>
                  {mypagePricesLoading ? '조회 중...' : `${Math.round(unrealizedProfitLoss) >= 0 ? '+' : ''}${Math.round(unrealizedProfitLoss).toLocaleString()}원`}
                </div>
              </div>

              <div className={`p-4 rounded-lg border ${parseFloat(profitRate) >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <div className={`text-sm mb-1 ${parseFloat(profitRate) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>수익률</div>
                <div className={`text-2xl font-bold ${parseFloat(profitRate) >= 0 ? 'text-emerald-900' : 'text-red-900'}`}>
                  {parseFloat(profitRate) >= 0 ? '+' : ''}{profitRate}%
                </div>
              </div>
            </div>

            {pieData.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">종목별 거래 비중</h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <RechartsPie>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </RechartsPie>
                  </ResponsiveContainer>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">보유 종목 현황</h4>
                  <div className="space-y-3">
                    {Object.entries(holdingsByStock).map(([name, data]) => {
                      const curPrice = currentPrices[name];
                      const unrealized = data.holdingQty > 0 && curPrice
                        ? Math.round((curPrice - data.avgBuyPrice) * data.holdingQty)
                        : null;
                      const unrealizedRate = data.avgBuyPrice > 0 && curPrice
                        ? (((curPrice - data.avgBuyPrice) / data.avgBuyPrice) * 100).toFixed(2)
                        : null;
                      return (
                        <div key={name} className="p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center justify-between mb-1">
                            <div className="font-medium text-gray-900">{name}</div>
                            <div className="text-sm text-gray-500">보유 {data.holdingQty}주</div>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-500">평균단가 {data.avgBuyPrice.toLocaleString()}원</span>
                            {curPrice && (
                              <span className="text-gray-500">현재가 {curPrice.toLocaleString()}원</span>
                            )}
                          </div>
                          {unrealized !== null && (
                            <div className={`text-sm font-medium mt-1 ${unrealized >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {unrealized >= 0 ? '+' : ''}{unrealized.toLocaleString()}원 ({unrealized >= 0 ? '+' : ''}{unrealizedRate}%)
                            </div>
                          )}
                          {data.holdingQty <= 0 && (
                            <div className="text-xs text-gray-400 mt-1">전량 매도 완료</div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {(portfolioTimelineLoading || portfolioTimeline.length > 0) && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-1 flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                포트폴리오 vs 시장 벤치마크
              </h3>
              <p className="text-sm text-gray-500 mb-4">첫 거래일 대비 수익률 비교 (%)</p>
              {portfolioTimelineLoading ? (
                <div className="flex items-center justify-center h-64 text-gray-400">조회 중...</div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={portfolioTimeline} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="displayDate" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis
                      tickFormatter={v => `${v > 0 ? '+' : ''}${v}%`}
                      tick={{ fontSize: 11 }}
                      width={55}
                    />
                    <Tooltip
                      formatter={(value, name) => {
                        if (value == null) return ['-', name];
                        const label = name === 'portfolioReturn' ? '내 포트폴리오'
                          : name === 'kospiReturn' ? 'KOSPI' : 'KOSDAQ';
                        return [`${value > 0 ? '+' : ''}${value}%`, label];
                      }}
                      labelStyle={{ color: '#374151' }}
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                    />
                    <Legend
                      formatter={v => v === 'portfolioReturn' ? '내 포트폴리오' : v === 'kospiReturn' ? 'KOSPI' : 'KOSDAQ'}
                    />
                    <Line type="monotone" dataKey="portfolioReturn" stroke="#0f172a" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls />
                    <Line type="monotone" dataKey="kospiReturn"     stroke="#3b82f6" strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} strokeDasharray="4 2" connectNulls />
                    <Line type="monotone" dataKey="kosdaqReturn"    stroke="#8b5cf6" strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} strokeDasharray="4 2" connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          )}

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              거래 통계
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="text-sm text-gray-600 mb-1">총 거래 횟수</div>
                <div className="text-2xl font-bold text-gray-900">{trades.length}건</div>
                <div className="text-xs text-gray-500 mt-1">
                  매수 {trades.filter(t => t.tradeType === 'buy').length}건 / 
                  매도 {trades.filter(t => t.tradeType === 'sell').length}건
                </div>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="text-sm text-gray-600 mb-1">거래 종목 수</div>
                <div className="text-2xl font-bold text-gray-900">{Object.keys(stockStats).length}개</div>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="text-sm text-gray-600 mb-1">평균 거래 금액</div>
                <div className="text-2xl font-bold text-gray-900">
                  {trades.length > 0 
                    ? Math.round(trades.reduce((sum, t) => sum + (parseFloat(t.price) * parseInt(t.quantity)), 0) / trades.length).toLocaleString() 
                    : 0}원
                </div>
              </div>
            </div>

            {topStocks.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">가장 많이 거래한 종목 TOP 5</h4>
                <div className="space-y-2">
                  {topStocks.map(([name, data], index) => (
                    <div key={name} className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                        index === 0 ? 'bg-yellow-100 text-yellow-800' :
                        index === 1 ? 'bg-gray-100 text-gray-700' :
                        index === 2 ? 'bg-orange-100 text-orange-700' :
                        'bg-gray-50 text-gray-600'
                      }`}>
                        {index + 1}
                      </div>
                      <div className="flex-1 flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium text-gray-900">{name}</span>
                        <span className="text-gray-600">{data.buyCount + data.sellCount}건</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              AI 분석 이력
            </h3>
            <p className="text-sm text-gray-500 mb-4">지금까지 실행한 AI 분석 내역</p>

            {performanceLoading ? (
              <div className="text-center py-8 text-gray-400 text-sm">불러오는 중...</div>
            ) : performanceData.filter(d => d.advice).length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">AI 분석 이력이 없습니다</p>
                <p className="text-xs mt-1">AI 분석 탭에서 분석을 실행해보세요</p>
              </div>
            ) : (
              <div className="space-y-2">
                {[...performanceData]
                  .filter(d => d.advice)
                  .sort((a, b) => new Date(b.analysisDate) - new Date(a.analysisDate))
                  .slice(0, 5)
                  .map(item => {
                    const strategyLabel = { bollinger: '볼린저 밴드', trend: '트렌드', external: '외부 전략' };
                    const isExpanded = expandedItemId === item.id;
                    return (
                      <div key={item.id} className="border border-gray-100 rounded-lg bg-gray-50 overflow-hidden">
                        <div className="flex items-center">
                          <button
                            onClick={() => setExpandedItemId(isExpanded ? null : item.id)}
                            className="flex-1 flex items-center justify-between px-4 py-3 text-left hover:bg-gray-100 transition-colors"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-gray-900">{item.stockName}</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                item.signal === 'buy'  ? 'bg-emerald-100 text-emerald-800' :
                                item.signal === 'sell' ? 'bg-red-100 text-red-800' :
                                                         'bg-blue-100 text-blue-800'
                              }`}>
                                {item.signal === 'buy' ? '추가매수' : item.signal === 'sell' ? '매도' : '보유'}
                              </span>
                              {item.totalScore != null && (
                                <span className="text-xs text-gray-500">{Math.round(item.totalScore)}점</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-400">
                              <span>{strategyLabel[item.strategyType] || item.strategyType}</span>
                              <span>·</span>
                              <span>{item.analysisDate}</span>
                              <span className="ml-1 text-gray-400">{isExpanded ? '▲' : '▼'}</span>
                            </div>
                          </button>
                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              if (!window.confirm('이 분석 결과를 삭제할까요?')) return;
                              try {
                                await stockApi.deleteAnalysisResult(item.id);
                                setPerformanceData(prev => prev.filter(p => p.id !== item.id));
                              } catch {
                                alert('삭제에 실패했습니다.');
                              }
                            }}
                            className="px-3 py-3 text-gray-300 hover:text-red-500 transition-colors"
                            title="삭제"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                        {isExpanded && (
                          <div className="px-4 pb-4 border-t border-gray-200">
                            {item.advice && (
                              <p className="text-sm text-gray-700 leading-relaxed mt-3">{item.advice}</p>
                            )}
                            {item.evaluation && (
                              <p className="text-xs text-gray-500 leading-relaxed border-t border-gray-200 pt-2 mt-2">{item.evaluation}</p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                }
                {performanceData.filter(d => d.advice).length > 5 && (
                  <p className="text-xs text-gray-400 text-right">
                    최근 5건 표시 · 전체 {performanceData.filter(d => d.advice).length}건
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Bookmark className="w-5 h-5" />
              저장한 전략
            </h3>
            
            {savedStrategies.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <Bookmark className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">저장한 전략이 없습니다</p>
                <p className="text-xs mt-1">외부 전략 URL을 저장해보세요</p>
              </div>
            ) : (
              <div className="space-y-2">
                {savedStrategies.map((item) => (
                  <div key={item.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="flex-1">
                      {item.name && <div className="text-sm font-medium text-gray-900 mb-0.5">{item.name}</div>}
                      <div className="text-xs text-gray-400 mb-1">저장일: {item.savedAt}</div>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-slate-600 hover:text-slate-900 break-all"
                      >
                        🔗 {item.url}
                      </a>
                    </div>
                    <button
                      onClick={() => removeSavedStrategy(item.id)}
                      className="text-red-500 hover:text-red-700 p-2 ml-2"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Download className="w-5 h-5" />
              데이터 관리
            </h3>
            
            <div className="space-y-3">
              <button onClick={downloadCSV} className="w-full bg-slate-900 text-white py-3 rounded-lg font-medium hover:bg-slate-800 transition-colors flex items-center justify-center gap-2">
                <Download className="w-4 h-4" />
                거래 내역 다운로드 (CSV)
              </button>

              <button onClick={downloadPDF} className="w-full bg-white text-slate-900 py-3 rounded-lg font-medium border-2 border-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-center gap-2">
                <BarChart3 className="w-4 h-4" />
                분석 결과 다운로드 (PDF)
              </button>

            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderAiPerformancePage = () => {
    const signalLabel = { buy: '추가매수', sell: '매도', hold: '보유' };
    const signalColor = {
      buy: 'bg-emerald-100 text-emerald-800',
      sell: 'bg-red-100 text-red-800',
      hold: 'bg-blue-100 text-blue-800',
    };

    const evaluated = performanceData.filter(d => d.isCorrect !== null);
    const correctCount = evaluated.filter(d => d.isCorrect).length;
    const accuracy = evaluated.length > 0 ? ((correctCount / evaluated.length) * 100).toFixed(1) : null;

    const pieData = [
      { name: '적중', value: correctCount },
      { name: '미적중', value: evaluated.length - correctCount },
    ];
    const PIE_COLORS = ['#10b981', '#f87171'];

    if (performanceLoading) {
      return (
        <div className="max-w-5xl mx-auto flex items-center justify-center h-64">
          <div className="text-gray-500">불러오는 중...</div>
        </div>
      );
    }

    return (
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900">AI 성과 분석</h2>
          <p className="text-gray-500 text-sm mt-1">AI 조언의 적중률과 수익 기여도를 확인하세요</p>
        </div>

        {performanceData.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-gray-400">
            아직 저장된 AI 분석 결과가 없습니다. AI 분석을 먼저 실행해주세요.
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <div className="text-sm text-gray-500 mb-1">전체 분석 건수</div>
                <div className="text-3xl font-bold text-gray-900">{performanceData.length}건</div>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <div className="text-sm text-gray-500 mb-1">평가 완료</div>
                <div className="text-3xl font-bold text-emerald-600">{correctCount}건 적중</div>
              </div>
              <div className={`rounded-lg border p-5 ${accuracy === null ? 'bg-gray-50 border-gray-200' : parseFloat(accuracy) >= 60 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <div className={`text-sm mb-1 ${accuracy === null ? 'text-gray-500' : parseFloat(accuracy) >= 60 ? 'text-emerald-600' : 'text-red-600'}`}>AI 적중률</div>
                <div className={`text-3xl font-bold ${accuracy === null ? 'text-gray-400' : parseFloat(accuracy) >= 60 ? 'text-emerald-700' : 'text-red-700'}`}>
                  {accuracy !== null ? `${accuracy}%` : '집계 중'}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h3 className="text-base font-semibold text-gray-900">조언별 결과 내역</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                      <tr>
                        <th className="px-4 py-3 text-left">종목</th>
                        <th className="px-4 py-3 text-left">분석일</th>
                        <th className="px-4 py-3 text-left">신호</th>
                        <th className="px-4 py-3 text-right">분석가격</th>
                        <th className="px-4 py-3 text-right">30일 후 가격</th>
                        <th className="px-4 py-3 text-right">수익률</th>
                        <th className="px-4 py-3 text-center">결과</th>
                        <th className="px-4 py-3"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {performanceData.map((item, idx) => {
                        const returnRate = item.priceAtEvaluation != null
                          ? (((item.priceAtEvaluation - item.priceAtAnalysis) / item.priceAtAnalysis) * 100).toFixed(1)
                          : null;
                        return (
                          <tr key={idx} className="hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-3 font-medium text-gray-900">{item.stockName}</td>
                            <td className="px-4 py-3 text-gray-500">{item.analysisDate}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${signalColor[item.signal] || 'bg-gray-100 text-gray-700'}`}>
                                {signalLabel[item.signal] || item.signal}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right text-gray-700">{item.priceAtAnalysis.toLocaleString()}원</td>
                            <td className="px-4 py-3 text-right text-gray-700">
                              {item.priceAtEvaluation != null ? `${item.priceAtEvaluation.toLocaleString()}원` : <span className="text-gray-400 text-xs">평가 대기</span>}
                            </td>
                            <td className={`px-4 py-3 text-right font-medium ${returnRate === null ? 'text-gray-400' : parseFloat(returnRate) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {returnRate !== null ? `${parseFloat(returnRate) >= 0 ? '+' : ''}${returnRate}%` : '-'}
                            </td>
                            <td className="px-4 py-3 text-center text-lg">
                              {item.isCorrect === null ? <span className="text-gray-400 text-xs">대기</span> : item.isCorrect ? '✅' : '❌'}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <button
                                onClick={async () => {
                                  if (!window.confirm('이 분석 결과를 삭제할까요?')) return;
                                  try {
                                    await stockApi.deleteAnalysisResult(item.id);
                                    setPerformanceData(prev => prev.filter(p => p.id !== item.id));
                                  } catch {
                                    alert('삭제에 실패했습니다.');
                                  }
                                }}
                                className="text-gray-300 hover:text-red-500 transition-colors"
                                title="삭제"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6 flex flex-col items-center justify-center">
                <h3 className="text-base font-semibold text-gray-900 mb-4 self-start">적중률 분포</h3>
                {evaluated.length === 0 ? (
                  <div className="text-gray-400 text-sm text-center">30일 후 자동 평가됩니다</div>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={220}>
                      <RechartsPie>
                        <Pie
                          data={pieData}
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={70}
                          dataKey="value"
                          labelLine={false}
                          label={({ name, percent, cx, cy, midAngle, outerRadius: or }) => {
                            const RADIAN = Math.PI / 180;
                            const x = cx + (or + 20) * Math.cos(-midAngle * RADIAN);
                            const y = cy + (or + 20) * Math.sin(-midAngle * RADIAN);
                            return (
                              <text x={x} y={y} textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" fontSize={12} fill="#374151">
                                {`${name} ${(percent * 100).toFixed(0)}%`}
                              </text>
                            );
                          }}
                        >
                          {pieData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={PIE_COLORS[index]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </RechartsPie>
                    </ResponsiveContainer>
                    <div className="flex gap-4 mt-2 text-xs text-gray-600">
                      <span className="flex items-center gap-1 whitespace-nowrap">
                        <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block flex-shrink-0" />적중
                      </span>
                      <span className="flex items-center gap-1 whitespace-nowrap">
                        <span className="w-3 h-3 rounded-full bg-red-400 inline-block flex-shrink-0" />미적중
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">

      {loading && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white rounded-2xl px-10 py-10 flex flex-col items-center gap-5 shadow-2xl">
            <div className="w-14 h-14 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin" />
            <div className="text-center">
              <p className="text-lg font-semibold text-gray-900">AI 분석 중입니다</p>
              <p className="text-sm text-gray-500 mt-1">잠시만 기다려주세요...</p>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-slate-900 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Inveskit</h1>
                <p className="text-gray-500 text-sm">스마트 투자 분석 도구</p>
              </div>
            </div>
          </div>
          
          <div className="flex gap-1 mt-6">
            <button
              onClick={() => setCurrentPage('input')}
              className={`px-5 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2 ${
                currentPage === 'input'
                  ? 'bg-slate-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <FileText className="w-4 h-4" />
              거래 입력
            </button>
            <button
              onClick={() => setCurrentPage('chart')}
              className={`px-5 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2 ${
                currentPage === 'chart'
                  ? 'bg-slate-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Activity className="w-4 h-4" />
              차트 분석
            </button>
            <button
              onClick={() => setCurrentPage('analysis')}
              className={`px-5 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2 ${
                currentPage === 'analysis'
                  ? 'bg-slate-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              AI 분석
            </button>
            <button
              onClick={() => setCurrentPage('ai-performance')}
              className={`px-5 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2 ${
                currentPage === 'ai-performance'
                  ? 'bg-slate-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Trophy className="w-4 h-4" />
              AI 성과
            </button>
            <button
              onClick={() => setCurrentPage('mypage')}
              className={`px-5 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2 ${
                currentPage === 'mypage'
                  ? 'bg-slate-900 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <User className="w-4 h-4" />
              마이페이지
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {currentPage === 'input' && renderInputPage()}
        {currentPage === 'chart' && renderChartPage()}
        {currentPage === 'analysis' && renderAnalysisPage()}
        {currentPage === 'ai-performance' && renderAiPerformancePage()}
        {currentPage === 'mypage' && renderMyPage()}
      </div>
    </div>
  );
};

export default StockTradingAnalyzer;