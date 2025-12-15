import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api';

const stockApi = {
  // ========== Stock APIs ==========
  
  // 60일 주가 데이터 조회
  getStockPrices: async (stockName, endDate) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stocks/prices`, {
        params: {
          stockName,
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

  // 거래 개수
  getTradeCount: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/trades/count`);
      return response.data;
    } catch (error) {
      console.error('거래 개수 조회 실패:', error);
      throw error;
    }
  }
};

export default stockApi;