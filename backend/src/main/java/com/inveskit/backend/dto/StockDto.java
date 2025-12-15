package com.inveskit.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class StockDto {
    private String name;
    private String code;
    private String market;
}