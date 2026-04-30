package com.inveskit.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inveskit.backend.dto.AnalysisRequest;
import com.inveskit.backend.dto.AnalysisResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

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
            // String으로 일단 받기
            String responseBody = webClient.post()
                    .uri(analysisApiUrl + "/api/analyze")
                    .bodyValue(request)
                    .retrieve()
                    .bodyToMono(String.class)
                    .block();

            log.info("Flask API 원본 응답: {}", responseBody);

            // 객체로 직접 파싱
            ObjectMapper mapper = new ObjectMapper();
            AnalysisResponse response = mapper.readValue(responseBody, AnalysisResponse.class);

            log.info("Flask API 응답 성공 - totalScore: {}, signal: {}",
                    response.getTotalScore(),
                    response.getSignal());

            return response;

        } catch (Exception e) {
            log.error("Flask API 호출 실패: {}", e.getMessage(), e);
            throw new RuntimeException("AI 분석 서비스 호출 실패: " + e.getMessage(), e);
        }
    }
}