package com.inveskit.backend.util;

import java.util.HashMap;
import java.util.Map;

public class StockCodeMapper {

    private static final Map<String, String> STOCK_CODE_MAP = new HashMap<>();

    static {
        // KOSPI 주요 종목
        STOCK_CODE_MAP.put("삼성전자", "005930");
        STOCK_CODE_MAP.put("SK하이닉스", "000660");
        STOCK_CODE_MAP.put("LG에너지솔루션", "373220");
        STOCK_CODE_MAP.put("삼성바이오로직스", "207940");
        STOCK_CODE_MAP.put("현대차", "005380");
        STOCK_CODE_MAP.put("기아", "000270");
        STOCK_CODE_MAP.put("POSCO홀딩스", "005490");
        STOCK_CODE_MAP.put("네이버", "035420");
        STOCK_CODE_MAP.put("카카오", "035720");
        STOCK_CODE_MAP.put("셀트리온", "068270");

        // 필요한 종목 계속 추가하기
    }

    public static String getStockCode(String stockName) {
        return STOCK_CODE_MAP.getOrDefault(stockName, "UNKNOWN");
    }

    public static boolean hasStockCode(String stockName) {
        return STOCK_CODE_MAP.containsKey(stockName);
    }
}