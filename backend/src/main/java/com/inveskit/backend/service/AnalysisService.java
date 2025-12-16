package com.inveskit.backend.service;

import com.inveskit.backend.dto.AnalysisRequest;
import com.inveskit.backend.dto.AnalysisResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@Slf4j
@Service
@RequiredArgsConstructor
public class AnalysisService {

    private final WebClient webClient;

    @Value("${analysis.api.url:https://aider-production-7367.up.railway.app}")
    private String analysisApiUrl;

    public AnalysisResponse analyzeTrading(AnalysisRequest request) {
        log.info("Flask API 호출 시작: {}", analysisApiUrl);
        log.info("요청 데이터 - trades: {}, stockPrices: {}, strategy: {}",
                request.getTrades().size(),
                request.getStockPrices().size(),
                request.getStrategy());

        try {
            AnalysisResponse response = webClient.post()
                    .uri(analysisApiUrl + "/api/analyze")
                    .bodyValue(request)
                    .retrieve()
                    .bodyToMono(AnalysisResponse.class)
                    .block();

            log.info("Flask API 응답 성공");
            return response;

        } catch (Exception e) {
            log.error("Flask API 호출 실패: {}", e.getMessage(), e);
            throw new RuntimeException("AI 분석 서비스 호출 실패: " + e.getMessage(), e);
        }
    }
}