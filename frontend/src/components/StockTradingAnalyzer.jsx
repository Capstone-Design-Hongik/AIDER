import React, { useState } from 'react';
import { TrendingUp, BarChart3, Plus, Trash2, AlertCircle, FileText, Activity, User, PieChart, Download, Bookmark } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceDot, PieChart as RechartsPie, Pie, Cell, BarChart, Bar } from 'recharts';
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

  const [strategy, setStrategy] = useState('bollinger');
  const [externalUrl, setExternalUrl] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savedStrategies, setSavedStrategies] = useState([]);

  const [stockData, setStockData] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState(null);

  const generateMockStockData = () => {
    const data = [];
    const basePrice = 70000;
    const today = new Date();
    
    for (let i = 59; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      
      const randomChange = (Math.random() - 0.5) * 3000;
      const price = basePrice + randomChange + (Math.sin(i / 10) * 2000);
      
      data.push({
        date: date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
        fullDate: date.toISOString().split('T')[0],
        close: Math.round(price),
        open: Math.round(price + (Math.random() - 0.5) * 1000),
        high: Math.round(price + Math.random() * 1500),
        low: Math.round(price - Math.random() * 1500)
      });
    }
    
    return data;
  };

  // 1. 컴포넌트 마운트 시 거래 내역 불러오기
React.useEffect(() => {
  const loadTrades = async () => {
    try {
      const allTrades = await stockApi.getAllTrades();
      setTrades(allTrades);
    } catch (error) {
      console.error('거래 내역 로딩 실패:', error);
    }
  };
  
  loadTrades();
}, []);

// 2. 차트 페이지에서 주가 데이터 불러오기
React.useEffect(() => {
  const fetchData = async () => {
    if (currentPage === 'chart' && trades.length > 0) {
      const stockName = trades[0].stockName;
      setChartLoading(true);
      setChartError(null);
      
      try {
        const latestTradeDate = trades
          .map(t => t.date)
          .sort()
          .reverse()[0];
        
        const response = await stockApi.getStockPrices(stockName, latestTradeDate);
        
        const formattedData = response.prices.map(p => ({
          date: new Date(p.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
          fullDate: p.date,
          close: p.closePrice
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
}, [currentPage, trades]);

  const handleStockNameChange = async (value) => {
  setCurrentTrade({...currentTrade, stockName: value});
  
  if (value.length > 0) {
    try {
      const results = await stockApi.searchStocks(value);
      setSearchResults(results);
      setShowDropdown(true);
    } catch (error) {
      console.error('검색 실패:', error);
      setSearchResults([]);
    }
  } else {
    setSearchResults([]);
    setShowDropdown(false);
    }
  };

  const selectStock = (stockName) => {
    setCurrentTrade({...currentTrade, stockName});
    setShowDropdown(false);
    setSearchResults([]);
  };


  const addTrade = async () => {
  if (currentTrade.stockName && currentTrade.date && currentTrade.price && currentTrade.quantity) {
    try {
      const response = await stockApi.createTrade(currentTrade);
      setTrades([...trades, response]);
      setCurrentTrade({
        stockName: '',
        tradeType: 'buy',
        date: '',
        price: '',
        quantity: ''
      });
    } catch (error) {
      console.error('거래 추가 실패:', error);
      alert('거래 추가에 실패했습니다.');
    }
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

  const analyzeTrading = () => {
    setLoading(true);
    
    setTimeout(() => {
      let mockAnalysis;
      
      if (strategy === 'external') {
        mockAnalysis = {
          strategy: '외부 전략',
          url: externalUrl,
          summary: `외부 콘텐츠를 기반으로 ${trades.length}건의 거래를 분석했습니다.`,
          advice: `제공하신 외부 전략 콘텐츠를 분석한 결과, 해당 전략의 핵심 원칙과 비교했을 때 다음과 같은 인사이트를 얻을 수 있습니다. 전략에서 강조하는 진입 시점과 실제 거래 타이밍 간의 일치도를 확인하고, 리스크 관리 측면에서의 개선점을 발견할 수 있습니다.`,
          metrics: {
            totalTrades: trades.length,
            avgPrice: (trades.reduce((sum, t) => sum + parseFloat(t.price), 0) / trades.length).toFixed(2),
            totalVolume: trades.reduce((sum, t) => sum + parseInt(t.quantity), 0)
          }
        };
      } else {
        mockAnalysis = {
          strategy: strategy === 'bollinger' ? '볼린저 밴드' : '추세추종',
          summary: `총 ${trades.length}건의 거래를 분석했습니다.`,
          advice: strategy === 'bollinger' 
            ? '볼린저 밴드 관점에서 분석한 결과, 상단 밴드 근처에서의 매수가 관찰됩니다. 과매수 구간에서의 진입은 리스크가 높을 수 있습니다. 중심선 부근에서의 매수 타이밍을 고려하고, 하단 밴드 이탈 시 손절매를 권장합니다.'
            : '추세추종 전략 관점에서 보면, 상승 추세 초기 진입이 효과적입니다. 현재 거래 패턴을 보면 추세 중후반부 진입이 다수 관찰되며, 이는 수익률을 제한할 수 있습니다. 이동평균선 골든크로스 시점 전후로 진입하고, 추세 전환 신호 발생 시 신속한 청산을 권장합니다.',
          metrics: {
            totalTrades: trades.length,
            avgPrice: (trades.reduce((sum, t) => sum + parseFloat(t.price), 0) / trades.length).toFixed(2),
            totalVolume: trades.reduce((sum, t) => sum + parseInt(t.quantity), 0)
          }
        };
      }
      
      setAnalysis(mockAnalysis);
      setLoading(false);
      setCurrentPage('analysis');
    }, 1500);
  };

  const saveStrategy = () => {
    if (strategy === 'external' && externalUrl) {
      const newStrategy = {
        id: Date.now(),
        type: 'external',
        url: externalUrl,
        savedAt: new Date().toISOString().split('T')[0]
      };
      setSavedStrategies([...savedStrategies, newStrategy]);
    }
  };

  const removeSavedStrategy = (id) => {
    setSavedStrategies(savedStrategies.filter(s => s.id !== id));
  };

  const renderInputPage = () => (
    <div className="max-w-6xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Plus className="w-5 h-5" />
              매매 기록 입력
            </h2>
            
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

              <button
                onClick={addTrade}
                className="w-full bg-slate-900 text-white py-2.5 rounded-lg font-medium hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                거래 추가
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              분석 전략 선택
            </h2>
            
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
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  전략 콘텐츠 URL
                </label>
                <input
                  type="url"
                  value={externalUrl}
                  onChange={(e) => setExternalUrl(e.target.value)}
                  placeholder="예: https://youtube.com/watch?v=..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
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
              </div>
            )}

            <button
              onClick={analyzeTrading}
              disabled={trades.length === 0 || loading || (strategy === 'external' && !externalUrl)}
              className="w-full mt-4 bg-emerald-600 text-white py-2.5 rounded-lg font-medium hover:bg-emerald-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? '분석 중...' : 'AI 분석 시작'}
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">입력된 거래 내역</h2>
            
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
                    <button
                      onClick={() => removeTrade(trade.id)}
                      className="text-red-500 hover:text-red-700 p-2"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  const renderChartPage = () => {
  const stockName = trades.length > 0 ? trades[0].stockName : null;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          {stockName || '종목'} 60일 주가 차트
        </h2>
        
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
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#fff', 
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                  }}
                  formatter={(value) => [`${Number(value).toLocaleString()}원`, '종가']}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="close" 
                  stroke="#0f172a" 
                  strokeWidth={2}
                  name="종가"
                  dot={false}
                />
                {trades.map((trade) => {
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
            
            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-800">
                ✅ 실제 주가 데이터가 표시되고 있습니다! (Yahoo Finance API)
              </p>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
};

  const renderAnalysisPage = () => (
    <div className="max-w-4xl mx-auto">
      {analysis ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">AI 분석 결과</h2>
          
          <div className="space-y-5">
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <div className="text-sm text-slate-600 mb-1">선택한 전략</div>
              <div className="text-lg font-semibold text-slate-900">{analysis.strategy}</div>
              {analysis.url && (
                <a 
                  href={analysis.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm text-slate-600 hover:text-slate-900 mt-1 block break-all"
                >
                  🔗 {analysis.url}
                </a>
              )}
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="text-xs text-gray-500 mb-1">총 거래</div>
                <div className="text-xl font-bold text-gray-900">{analysis.metrics.totalTrades}건</div>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="text-xs text-gray-500 mb-1">평균 단가</div>
                <div className="text-xl font-bold text-gray-900">{parseFloat(analysis.metrics.avgPrice).toLocaleString()}원</div>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="text-xs text-gray-500 mb-1">총 수량</div>
                <div className="text-xl font-bold text-gray-900">{analysis.metrics.totalVolume}주</div>
              </div>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
              <div className="text-sm font-semibold text-blue-900 mb-2">💡 AI 조언</div>
              <div className="text-sm text-blue-800 leading-relaxed">
                {analysis.advice}
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
    const totalInvestment = trades.reduce((sum, t) => {
      if (t.tradeType === 'buy') {
        return sum + (parseFloat(t.price) * parseInt(t.quantity));
      }
      return sum;
    }, 0);

    const totalSales = trades.reduce((sum, t) => {
      if (t.tradeType === 'sell') {
        return sum + (parseFloat(t.price) * parseInt(t.quantity));
      }
      return sum;
    }, 0);

    const profitLoss = totalSales - totalInvestment;
    const profitRate = totalInvestment > 0 ? ((profitLoss / totalInvestment) * 100).toFixed(2) : 0;

    const stockStats = {};
    trades.forEach(trade => {
      if (!stockStats[trade.stockName]) {
        stockStats[trade.stockName] = { buy: 0, sell: 0, count: 0 };
      }
      stockStats[trade.stockName].count++;
      if (trade.tradeType === 'buy') {
        stockStats[trade.stockName].buy++;
      } else {
        stockStats[trade.stockName].sell++;
      }
    });

    const topStocks = Object.entries(stockStats)
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 5);

    const pieData = Object.entries(stockStats).map(([name, data]) => ({
      name,
      value: data.count
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
              
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                <div className="text-sm text-slate-600 mb-1">총 매도금액</div>
                <div className="text-2xl font-bold text-slate-900">
                  {totalSales.toLocaleString()}원
                </div>
              </div>
              
              <div className={`p-4 rounded-lg border ${profitLoss >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <div className={`text-sm mb-1 ${profitLoss >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>손익</div>
                <div className={`text-2xl font-bold ${profitLoss >= 0 ? 'text-emerald-900' : 'text-red-900'}`}>
                  {profitLoss >= 0 ? '+' : ''}{profitLoss.toLocaleString()}원
                </div>
              </div>
              
              <div className={`p-4 rounded-lg border ${profitRate >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <div className={`text-sm mb-1 ${profitRate >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>수익률</div>
                <div className={`text-2xl font-bold ${profitRate >= 0 ? 'text-emerald-900' : 'text-red-900'}`}>
                  {profitRate >= 0 ? '+' : ''}{profitRate}%
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
                    {Object.entries(stockStats).map(([name, data]) => (
                      <div key={name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <div className="font-medium text-gray-900">{name}</div>
                          <div className="text-sm text-gray-500">
                            매수 {data.buy}건 | 매도 {data.sell}건
                            </div>
                        </div>
                        <div className="text-lg font-bold text-gray-900">{data.count}건</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

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
                        <span className="text-gray-600">{data.count}건</span>
                      </div>
                    </div>
                  ))}
                </div>
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
                      <div className="text-sm text-gray-500 mb-1">저장일: {item.savedAt}</div>
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
              <button className="w-full bg-slate-900 text-white py-3 rounded-lg font-medium hover:bg-slate-800 transition-colors flex items-center justify-center gap-2">
                <Download className="w-4 h-4" />
                거래 내역 다운로드 (CSV)
              </button>
              
              <button className="w-full bg-white text-slate-900 py-3 rounded-lg font-medium border-2 border-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-center gap-2">
                <BarChart3 className="w-4 h-4" />
                분석 결과 다운로드 (PDF)
              </button>

              <div className="pt-4 border-t border-gray-200">
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div className="text-sm font-medium text-amber-900 mb-2">💡 투자 팁</div>
                  <ul className="text-xs text-amber-800 space-y-1">
                    <li>• 정기적으로 거래 내역을 백업하세요</li>
                    <li>• 전략별 성과를 비교 분석해보세요</li>
                    <li>• 손절 원칙을 정하고 지키세요</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
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
        {currentPage === 'mypage' && renderMyPage()}
      </div>
    </div>
  );
};

export default StockTradingAnalyzer;