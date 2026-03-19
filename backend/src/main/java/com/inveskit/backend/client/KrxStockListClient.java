package com.inveskit.backend.client;

import com.inveskit.backend.domain.StockInfo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Slf4j
public class KrxStockListClient {

    private static final String KRX_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd";

    private final WebClient webClient;

    public List<StockInfo> fetchAllStocks() {
        List<StockInfo> all = new ArrayList<>();
        all.addAll(fetchByMarket("STK", "KOSPI"));
        all.addAll(fetchByMarket("KSQ", "KOSDAQ"));
        log.info("KRX 전체 종목 수: {}", all.size());
        return all;
    }

    @SuppressWarnings("unchecked")
    private List<StockInfo> fetchByMarket(String mktId, String marketName) {
        MultiValueMap<String, String> formData = new LinkedMultiValueMap<>();
        formData.add("bld", "dbms/MDC/STAT/standard/MDCSTAT01901");
        formData.add("mktId", mktId);
        formData.add("share", "1");
        formData.add("csvxls_isNo", "false");

        try {
            Map<String, Object> response = webClient.post()
                    .uri(KRX_URL)
                    .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    .header("Referer", "https://data.krx.co.kr/contents/MDC/MDI/mdiBoardDetail/mdiBoardDetail_MDCSTAT01901.cmd")
                    .header("Accept", "application/json, text/javascript, */*; q=0.01")
                    .header("X-Requested-With", "XMLHttpRequest")
                    .body(BodyInserters.fromFormData(formData))
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

            if (response == null) {
                log.warn("KRX {} 응답 없음", marketName);
                return Collections.emptyList();
            }

            List<Map<String, Object>> output = (List<Map<String, Object>>) response.get("output");
            if (output == null) {
                log.warn("KRX {} output 없음", marketName);
                return Collections.emptyList();
            }

            List<StockInfo> stocks = output.stream()
                    .filter(item -> item.get("ISU_SRT_CD") != null && item.get("ISU_ABBRV") != null)
                    .map(item -> StockInfo.builder()
                            .stockCode((String) item.get("ISU_SRT_CD"))
                            .stockName((String) item.get("ISU_ABBRV"))
                            .market(marketName)
                            .build())
                    .toList();

            log.info("KRX {} 종목 수: {}", marketName, stocks.size());
            return stocks;

        } catch (Exception e) {
            log.error("KRX {} 조회 실패: {}", marketName, e.getMessage());
            return Collections.emptyList();
        }
    }
}
