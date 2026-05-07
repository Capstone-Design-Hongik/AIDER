package com.inveskit.backend.controller;

import com.inveskit.backend.domain.SavedStrategy;
import com.inveskit.backend.service.SavedStrategyService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/strategies")
@RequiredArgsConstructor
public class StrategyController {

    private final SavedStrategyService savedStrategyService;

    @GetMapping
    public List<SavedStrategy> getAll() {
        return savedStrategyService.findAll();
    }

    @PostMapping
    public ResponseEntity<?> save(@RequestBody Map<String, String> body) {
        String url = body.get("url");
        if (url == null || url.isBlank()) {
            return ResponseEntity.badRequest().body("URL이 필요합니다.");
        }
        try {
            SavedStrategy saved = savedStrategyService.save(url);
            return ResponseEntity.ok(saved);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        savedStrategyService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
