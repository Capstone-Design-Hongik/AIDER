package com.inveskit.backend.client;

import com.inveskit.backend.domain.StockInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Component
@Slf4j
public class CsvStockLoader {

    private static final String CSV_PATH = "data/korean_stocks.csv";

    public List<StockInfo> loadFromCsv() {
        try {
            ClassPathResource resource = new ClassPathResource(CSV_PATH);
            List<StockInfo> stocks = new ArrayList<>();

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8))) {

                String line;
                boolean firstLine = true;

                while ((line = reader.readLine()) != null) {
                    if (firstLine) { firstLine = false; continue; } // 헤더 스킵
                    if (line.isBlank()) continue;

                    String[] parts = line.split(",");
                    if (parts.length < 3) continue;

                    stocks.add(StockInfo.builder()
                            .stockCode(parts[0].trim())
                            .stockName(parts[1].trim())
                            .market(parts[2].trim())
                            .build());
                }
            }

            log.info("CSV에서 {}개 종목 로드 완료", stocks.size());
            return stocks;

        } catch (Exception e) {
            log.error("CSV 로드 실패: {}", e.getMessage());
            return Collections.emptyList();
        }
    }
}
