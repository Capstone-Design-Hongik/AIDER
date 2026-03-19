package com.inveskit.backend.service;

import com.inveskit.backend.client.StockPriceData;
import com.inveskit.backend.client.YahooFinanceClient;
import com.inveskit.backend.domain.StockInfo;
import com.inveskit.backend.domain.StockPrice;
import com.inveskit.backend.dto.StockPriceResponse;
import com.inveskit.backend.repository.StockPriceRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class StockPriceService {

    private final StockPriceRepository stockPriceRepository;
    private final YahooFinanceClient yahooFinanceClient;
    private final StockInfoService stockInfoService;

    // 특정 종목의 60일 주가 데이터 조회
    public StockPriceResponse getStockPrices(String stockName, LocalDate endDate) {
        LocalDate startDate = endDate.minusDays(60);

        log.info("Fetching stock prices for {} from {} to {}", stockName, startDate, endDate);

        List<StockPrice> prices = stockPriceRepository.findByStockNameAndDateRange(
                stockName, startDate, endDate
        );

        if (prices.isEmpty()) {
            throw new RuntimeException("해당 종목의 주가 데이터가 없습니다: " + stockName);
        }

        return StockPriceResponse.builder()
                .stockName(stockName)
                .stockCode(prices.get(0).getStockCode())
                .prices(prices.stream()
                        .map(p -> StockPriceResponse.DailyPrice.builder()
                                .date(p.getTradeDate())
                                .closePrice(p.getClosePrice())
                                .build())
                        .collect(Collectors.toList()))
                .build();
    }

    // 종목명으로 코드를 stock_info에서 조회 후 Yahoo Finance에서 주가 데이터 초기화
    @Transactional
    public void initializeStockData(String stockName) {
        StockInfo info = stockInfoService.findByName(stockName);
        String stockCode = info.getStockCode();
        String market = info.getMarket();

        LocalDate startDate = LocalDate.of(2025, 1, 1);
        LocalDate endDate = LocalDate.now();

        log.info("Initializing stock data for {} ({}) from {} to {}",
                stockName, stockCode, startDate, endDate);

        // 코스피: .KS, 코스닥: .KQ
        String yahooSuffix = "KOSDAQ".equals(market) ? ".KQ" : ".KS";
        String yahooSymbol = stockCode + yahooSuffix;
        List<StockPriceData> priceDataList = yahooFinanceClient.fetchStockPrices(
                yahooSymbol, startDate, endDate
        );

        if (priceDataList.isEmpty()) {
            log.warn("No data fetched for {}", stockName);
            return;
        }

        // DB 저장 (중복 체크)
        int savedCount = 0;
        for (StockPriceData data : priceDataList) {
            if (!stockPriceRepository.existsByStockCodeAndTradeDate(stockCode, data.getDate())) {
                StockPrice stockPrice = StockPrice.builder()
                        .stockCode(stockCode)
                        .stockName(stockName)
                        .market(market)
                        .tradeDate(data.getDate())
                        .closePrice(data.getClosePrice())
                        .build();

                stockPriceRepository.save(stockPrice);
                savedCount++;
            }
        }

        log.info("Saved {} price records for {}", savedCount, stockName);
    }

    // 하위 호환용 오버로드 (stockCode, market을 직접 넘기는 경우)
    @Transactional
    public void initializeStockData(String stockName, String stockCode, String market) {
        LocalDate startDate = LocalDate.of(2025, 1, 1);
        LocalDate endDate = LocalDate.now();

        log.info("Initializing stock data for {} ({}) from {} to {}",
                stockName, stockCode, startDate, endDate);

        String yahooSuffix = "KOSDAQ".equals(market) ? ".KQ" : ".KS";
        String yahooSymbol = stockCode + yahooSuffix;
        List<StockPriceData> priceDataList = yahooFinanceClient.fetchStockPrices(
                yahooSymbol, startDate, endDate
        );

        if (priceDataList.isEmpty()) {
            log.warn("No data fetched for {}", stockName);
            return;
        }

        int savedCount = 0;
        for (StockPriceData data : priceDataList) {
            if (!stockPriceRepository.existsByStockCodeAndTradeDate(stockCode, data.getDate())) {
                StockPrice stockPrice = StockPrice.builder()
                        .stockCode(stockCode)
                        .stockName(stockName)
                        .market(market)
                        .tradeDate(data.getDate())
                        .closePrice(data.getClosePrice())
                        .build();

                stockPriceRepository.save(stockPrice);
                savedCount++;
            }
        }

        log.info("Saved {} price records for {}", savedCount, stockName);
    }

    //DB에 저장된 데이터 개수 확인
    public long getDataCount() {
        return stockPriceRepository.count();
    }

    public List<String> searchStockNames(String keyword) {
        log.info("Searching for stocks with keyword: {}", keyword);
        return stockInfoService.searchByKeyword(keyword);
    }
}
