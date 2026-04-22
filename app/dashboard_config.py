from __future__ import annotations

DISPLAY_YEAR_OFFSET = 0

PARAMETERS = {
    "aan_growth": {
        "label": "ААН нэгж нэмэгдэх он",
        "real_name": "Аж ахуйн нэмэгдэх он",
        "unit": "он",
        "value_format": "integer",
        "fallback_min": 0,
        "fallback_max": 50,
        "fallback_step": 1,
        "fallback_default": 0,
    },
    "aan_cluster": {
        "label": "ААН нэгжийн бүс",
        "real_name": "Аж ахуйн нэгжийн бүс",
        "unit": "тоо",
        "value_format": "integer",
        "fallback_min": 0,
        "fallback_max": 200,
        "fallback_step": 1,
        "fallback_default": 90,
    },
    "housing_zone": {
        "label": "Суурьшлийн бүс",
        "real_name": "Суурьшлийн бүс",
        "unit": "тоо",
        "value_format": "integer",
        "fallback_min": 0,
        "fallback_max": 500,
        "fallback_step": 1,
        "fallback_default": 243,
    },
    "job_density": {
        "label": "Нэг ААН хамаарах ажлын байр",
        "real_name": "Нэг ААН хамаарах ажлын байр",
        "unit": "тоо",
        "value_format": "integer",
        "fallback_min": 0,
        "fallback_max": 50,
        "fallback_step": 1,
        "fallback_default": 20,
    },
    "labor_participation": {
        "label": "Хөдөлмөрийн оролцоо",
        "real_name": "Хөдөлмөрийн оролцоо",
        "unit": "хувь",
        "value_format": "decimal_2",
        "fallback_min": 0,
        "fallback_max": 1,
        "fallback_step": 0.01,
        "fallback_default": 0.30,
    },
    "business_tax": {
        "label": "Бизнесийн татвар",
        "real_name": "Безнесийн бүтцэд ногдох татвар",
        "unit": "тоо",
        "value_format": "integer",
        "fallback_min": 0,
        "fallback_max": 1000,
        "fallback_step": 1,
        "fallback_default": 300,
    },
}

CHARTS = {
    "aan": {
        "label": "ААН",
        "real_name": "ААН",
        "canvas_id": "chart_aan",
        "unit": "нэгж",
    },
    "population": {
        "label": "Хүн ам",
        "real_name": "Хүн ам",
        "canvas_id": "chart_population",
        "unit": "хүн",
    },
    "housing": {
        "label": "Орон сууц",
        "real_name": "Орон сууц",
        "canvas_id": "chart_housing",
        "unit": "тоо",
    },
    "attraction": {
        "label": "Татах чадвар",
        "real_name": "Татах чадвар",
        "canvas_id": "chart_attraction",
        "unit": "индекс",
    },
    "jobs": {
        "label": "Ажлын байр",
        "real_name": "Ажлын байр",
        "canvas_id": "chart_jobs",
        "unit": "тоо",
    },
    "migration": {
        "label": "Шилжин ирэлт",
        "real_name": "Шилжин ирэлт",
        "canvas_id": "chart_migration",
        "unit": "хүн",
    },
    "labor": {
        "label": "Ажиллах хүч",
        "real_name": "Ажиллах хүч",
        "canvas_id": "chart_labor",
        "unit": "хүн",
    },
    "passenger": {
        "label": "Зорчигч",
        "real_name": "Зорчигч",
        "canvas_id": "chart_passenger",
        "unit": "хүн",
    },
    "education": {
        "label": "Боловсролын салбар",
        "real_name": "Боловсролын салбар",
        "canvas_id": "chart_education",
        "unit": "индекс",
    },
    "service": {
        "label": "Үйлчилгээ",
        "real_name": "Үйлчилгээний байгууламж чанар",
        "canvas_id": "chart_service",
        "unit": "индекс",
    },
}

CHART_ORDER = [
    "aan",
    "population",
    "housing",
    "attraction",
    "jobs",
    "migration",
    "labor",
    "passenger",
    "education",
    "service",
]