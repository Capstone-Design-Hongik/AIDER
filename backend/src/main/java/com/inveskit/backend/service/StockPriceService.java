package com.inveskit.backend.service;

import com.inveskit.backend.client.StockPriceData;
import com.inveskit.backend.client.YahooFinanceClient;
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

    //2025.01.01 부터 현재(2025.12.04)까지의 종가 데이터 DB에 저장하는 용도
    @Transactional
    public void initializeStockData(String stockName, String stockCode, String market) {
        LocalDate startDate = LocalDate.of(2025, 1, 1);
        LocalDate endDate = LocalDate.now();

        log.info("Initializing stock data for {} ({}) from {} to {}",
                stockName, stockCode, startDate, endDate);

        // Yahoo Finance에서 데이터 가져오기
        String yahooSymbol = stockCode + ".KS";  // 코스피: .KS, 코스닥: .KQ
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

    //DB에 저장된 데이터 개수 확인
    public long getDataCount() {
        return stockPriceRepository.count();
    }

    @Transactional(readOnly = true)
    public List<String> searchStockNames(String keyword) {
        log.info("Searching for stocks with keyword: {}", keyword);

        List<String> allStocks = stockPriceRepository.findDistinctStockNames();

        return allStocks.stream()
                .filter(name -> name.contains(keyword))
                .limit(10)
                .collect(Collectors.toList());
    }
}
