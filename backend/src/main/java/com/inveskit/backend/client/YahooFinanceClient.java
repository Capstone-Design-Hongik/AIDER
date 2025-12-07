package com.inveskit.backend.client;

import lombok.RequiredArgsConstructor;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.beans.factory.annotation.Value;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Slf4j
public class YahooFinanceClient {
    private final WebClient webClient;

    @Value("${yahoo.finance.base-url}")
    private String baseUrl;

    public List<StockPriceData> fetchStockPrices(String symbol, LocalDate startDate, LocalDate endDate) {
        long period1 = startDate.atStartOfDay(ZoneId.systemDefault()).toEpochSecond();
        long period2 = endDate.atTime(23, 59, 59).atZone(ZoneId.systemDefault()).toEpochSecond();

        String url = String.format(
                "%s/v8/finance/chart/%s?period1=%d&period2=%d&interval=1d",
                baseUrl, symbol, period1, period2
        );

        log.info("=== Yahoo Finance URL ===");
        log.info(url);
        log.info("Fetching stock prices for {} from {} to {}", symbol, startDate, endDate);

        try {
            Map<String, Object> response = webClient.get()
                    .uri(url)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

            log.info("=== Response received ===");
            log.info("Response: {}", response);

            return parseYahooResponse(response);

        } catch (Exception e) {
            log.error("Error fetching stock prices for symbol: {}", symbol, e);
            return Collections.emptyList();
        }
    }

    @SuppressWarnings("unchecked")
    private List<StockPriceData> parseYahooResponse(Map<String, Object> response) {
        try {
            Map<String, Object> chart = (Map<String, Object>) response.get("chart");
            List<Map<String, Object>> results = (List<Map<String, Object>>) chart.get("result");

            if (results == null || results.isEmpty()) {
                log.warn("No results in Yahoo Finance response");
                return Collections.emptyList();
            }

            Map<String, Object> result = results.get(0);
            List<Object> timestampObjects = (List<Object>) result.get("timestamp");

            Map<String, Object> indicators = (Map<String, Object>) result.get("indicators");
            List<Map<String, Object>> quotes = (List<Map<String, Object>>) indicators.get("quote");

            if (quotes == null || quotes.isEmpty()) {
                log.warn("No quotes in Yahoo Finance response");
                return Collections.emptyList();
            }

            Map<String, Object> quote = quotes.get(0);
            List<Object> closes = (List<Object>) quote.get("close");

            List<StockPriceData> prices = new ArrayList<>();

            // 타임스탬프 객체가 null이 아니고, 닫힌 가격 객체의 크기와 일치하는지 확인
            if (timestampObjects == null || timestampObjects.size() != closes.size()) {
                log.error("Timestamp and Close Price data size mismatch or Timestamp is null.");
                return Collections.emptyList();
            }

            for (int i = 0; i < timestampObjects.size(); i++) {

                Object timestampObj = timestampObjects.get(i);
                if (timestampObj == null) {
                    continue; // null 데이터는 스킵
                }

                Long timestamp = convertObjectToLong(timestampObj);

                LocalDate date = Instant.ofEpochSecond(timestamp)
                        .atZone(ZoneId.systemDefault())
                        .toLocalDate();

                Object closeObj = closes.get(i);
                if (closeObj == null) {
                    continue;  // null 데이터는 스킵
                }

                BigDecimal closePrice = new BigDecimal(closeObj.toString());

                prices.add(StockPriceData.builder()
                        .date(date)
                        .closePrice(closePrice)
                        .build());
            }

            log.info("Parsed {} price data points", prices.size());
            return prices;

        } catch (Exception e) {
            log.error("Error parsing Yahoo Finance response", e);
            return Collections.emptyList();
        }
    }

    private Long convertObjectToLong(Object obj) {
        if (obj instanceof Integer) {
            return ((Integer) obj).longValue();
        } else if (obj instanceof Long) {
            return (Long) obj;
        } else if (obj instanceof Number) {
            return ((Number) obj).longValue();
        }
        // 그 외 예상치 못한 타입이나 null이면 0 또는 null 처리
        throw new IllegalArgumentException("Cannot convert object to Long: " + obj.getClass().getName());
    }
}
