import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api';

const stockApi = {
  // ========== Stock APIs ==========
  
  getStockPrices: async (stockName, endDate, startDate) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stocks/prices`, {
        params: {
          stockName,
          startDate: startDate || undefined,
          endDate: endDate || undefined
        }
      });
      return response.data;
    } catch (error) {
      console.error('주가 데이터 조회 실패:', error);
      throw error;
    }
  },

  // 종목 데이터 초기화
  initializeStock: async (stockName, stockCode, market = 'KOSPI') => {
    try {
      const response = await axios.post(`${API_BASE_URL}/stocks/initialize`, null, {
        params: {
          stockName,
          stockCode,
          market
        }
      });
      return response.data;
    } catch (error) {
      console.error('데이터 초기화 실패:', error);
      throw error;
    }
  },

  // 저장된 데이터 개수 확인
  getDataCount: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stocks/count`);
      return response.data;
    } catch (error) {
      console.error('데이터 개수 조회 실패:', error);
      throw error;
    }
  },

  // 종목 검색 (자동완성)
  searchStocks: async (keyword) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stocks/search`, {
        params: { keyword }
      });
      return response.data;
    } catch (error) {
      console.error('종목 검색 실패:', error);
      throw error;
    }
  },

  // ========== Trade APIs ==========
  
  // 거래 생성
  createTrade: async (trade) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/trades`, {
        stockName: trade.stockName,
        tradeType: trade.tradeType,
        date: trade.date,
        price: parseFloat(trade.price),
        quantity: parseInt(trade.quantity)
      });
      return response.data;
    } catch (error) {
      console.error('거래 생성 실패:', error);
      throw error;
    }
  },

  // 전체 거래 조회
  getAllTrades: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/trades`);
      return response.data;
    } catch (error) {
      console.error('거래 조회 실패:', error);
      throw error;
    }
  },

  // 특정 거래 조회
  getTrade: async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/trades/${id}`);
      return response.data;
    } catch (error) {
      console.error('거래 조회 실패:', error);
      throw error;
    }
  },

  // 특정 종목 거래 조회
  getTradesByStock: async (stockName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/trades/stock/${stockName}`);
      return response.data;
    } catch (error) {
      console.error('종목별 거래 조회 실패:', error);
      throw error;
    }
  },

  // 거래 수정
  updateTrade: async (id, trade) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/trades/${id}`, {
        stockName: trade.stockName,
        tradeType: trade.tradeType,
        date: trade.date,
        price: parseFloat(trade.price),
        quantity: parseInt(trade.quantity)
      });
      return response.data;
    } catch (error) {
      console.error('거래 수정 실패:', error);
      throw error;
    }
  },

  // 거래 삭제
  deleteTrade: async (id) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/trades/${id}`);
      return response.data;
    } catch (error) {
      console.error('거래 삭제 실패:', error);
      throw error;
    }
  },

  // 전체 거래 삭제
  deleteAllTrades: async () => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/trades`);
      return response.data;
    } catch (error) {
      console.error('전체 거래 삭제 실패:', error);
      throw error;
    }
  },

  // 거래 개수
  getTradeCount: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/trades/count`);
      return response.data;
    } catch (error) {
      console.error('거래 개수 조회 실패:', error);
      throw error;
    }
  },

  // ========== Analysis API ==========
  // AI 분석 요청
  analyzeTrading: async (strategy, externalUrl = null, stockName = null) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/analysis`, {
        strategy,
        externalUrl,
        stockName
      });
      return response.data;
    } catch (error) {
      console.error('AI 분석 실패:', error);
      throw error;
    }
  },

  // AI 성과 조회
  getAiPerformance: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/analysis/performance`);
      return response.data;
    } catch (error) {
      console.error('AI 성과 조회 실패:', error);
      throw error;
    }
  },

  // AI 성과 결과 삭제
  deleteAnalysisResult: async (id) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/analysis/performance/${id}`);
      return response.data;
    } catch (error) {
      console.error('분석 결과 삭제 실패:', error);
      throw error;
    }
  },

  // ========== Strategy APIs ==========

  getSavedStrategies: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/strategies`);
      return response.data;
    } catch (error) {
      console.error('전략 조회 실패:', error);
      throw error;
    }
  },

  saveStrategy: async (url) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/strategies`, { url });
      return response.data;
    } catch (error) {
      console.error('전략 저장 실패:', error);
      throw error;
    }
  },

  deleteStrategy: async (id) => {
    try {
      await axios.delete(`${API_BASE_URL}/strategies/${id}`);
    } catch (error) {
      console.error('전략 삭제 실패:', error);
      throw error;
    }
  },

  // ========== Index APIs ==========
  getIndexPrices: async (name, startDate) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stocks/index`, {
        params: { name, startDate: startDate || undefined }
      });
      return response.data;
    } catch (error) {
      console.error(`${name} 지수 조회 실패:`, error);
      return [];
    }
  }
};

export default stockApi;