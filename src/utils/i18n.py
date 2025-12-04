"""
国际化(i18n)和语言检测模块
提供多语言支持和状态消息翻译
"""

import re
from typing import Dict


# 状态消息翻译字典
# 支持语言: en (英语), zh (简体中文), zh-tw (繁体中文), ja (日语), nl (荷兰语),
#          fr (法语), de (德语), es (西班牙语), it (意大利语), ru (俄语)
STATUS_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "started": {
        "en": "BP generation started",
        "zh": "商业计划书生成已开始",
        "zh-tw": "商業計劃書生成已開始",
        "ja": "ビジネスプラン生成を開始しました",
        "nl": "BP-generatie gestart",
        "fr": "Génération du plan d'affaires démarrée",
        "de": "BP-Generierung gestartet",
        "es": "Generación del plan de negocio iniciada",
        "it": "Generazione del piano aziendale avviata",
        "ru": "Генерация бизнес-плана начата"
    },
    "input_check": {
        "en": "Checking input completeness...",
        "zh": "正在检查输入完整性...",
        "zh-tw": "正在檢查輸入完整性...",
        "ja": "入力の完全性を確認中...",
        "nl": "Invoer volledigheid controleren...",
        "fr": "Vérification de l'exhaustivité de la saisie...",
        "de": "Eingabevollständigkeit prüfen...",
        "es": "Verificando la integridad de la entrada...",
        "it": "Verifica della completezza dell'input...",
        "ru": "Проверка полноты ввода..."
    },
    "structure_generation": {
        "en": "Generating BP structure...",
        "zh": "正在生成商业计划书结构...",
        "zh-tw": "正在生成商業計劃書結構...",
        "ja": "ビジネスプラン構造を生成中...",
        "nl": "BP-structuur genereren...",
        "fr": "Génération de la structure du plan d'affaires...",
        "de": "BP-Struktur generieren...",
        "es": "Generando la estructura del plan de negocio...",
        "it": "Generazione della struttura del piano aziendale...",
        "ru": "Генерация структуры бизнес-плана..."
    },
    "structure_regeneration": {
        "en": "Regenerating BP structure...",
        "zh": "正在重新生成商业计划书结构...",
        "zh-tw": "正在重新生成商業計劃書結構...",
        "ja": "ビジネスプラン構造を再生成中...",
        "nl": "BP-structuur opnieuw genereren...",
        "fr": "Régénération de la structure du plan d'affaires...",
        "de": "BP-Struktur erneut generieren...",
        "es": "Regenerando la estructura del plan de negocio...",
        "it": "Rigenerazione della struttura del piano aziendale...",
        "ru": "Повторная генерация структуры бизнес-плана..."
    },
    "structure_evaluation": {
        "en": "Evaluating BP structure...",
        "zh": "正在评估商业计划书结构...",
        "zh-tw": "正在評估商業計劃書結構...",
        "ja": "ビジネスプラン構造を評価中...",
        "nl": "BP-structuur evalueren...",
        "fr": "Évaluation de la structure du plan d'affaires...",
        "de": "BP-Struktur bewerten...",
        "es": "Evaluando la estructura del plan de negocio...",
        "it": "Valutazione della struttura del piano aziendale...",
        "ru": "Оценка структуры бизнес-плана..."
    },
    "painpoint_enhancement": {
        "en": "Enhancing pain points...",
        "zh": "正在优化痛点分析...",
        "zh-tw": "正在優化痛點分析...",
        "ja": "ペインポイントを強化中...",
        "nl": "Pijnpunten verbeteren...",
        "fr": "Amélioration des points de douleur...",
        "de": "Schmerzpunkte verbessern...",
        "es": "Mejorando los puntos de dolor...",
        "it": "Miglioramento dei punti critici...",
        "ru": "Улучшение болевых точек..."
    },
    "investor_evaluation": {
        "en": "Evaluating investor perspective...",
        "zh": "正在评估投资者视角...",
        "zh-tw": "正在評估投資者視角...",
        "ja": "投資家の視点を評価中...",
        "nl": "Investeerderperspectief evalueren...",
        "fr": "Évaluation de la perspective des investisseurs...",
        "de": "Investorenperspektive bewerten...",
        "es": "Evaluando la perspectiva del inversor...",
        "it": "Valutazione della prospettiva dell'investitore...",
        "ru": "Оценка перспективы инвестора..."
    },
    "pitch_generation": {
        "en": "Generating 60-second pitch...",
        "zh": "正在生成60秒路演...",
        "zh-tw": "正在生成60秒路演...",
        "ja": "60秒ピッチを生成中...",
        "nl": "60-seconden pitch genereren...",
        "fr": "Génération du pitch de 60 secondes...",
        "de": "60-Sekunden-Pitch generieren...",
        "es": "Generando el pitch de 60 segundos...",
        "it": "Generazione del pitch di 60 secondi...",
        "ru": "Генерация 60-секундной презентации..."
    },
    "ppt_generation": {
        "en": "Generating PPT design...",
        "zh": "正在生成PPT设计...",
        "zh-tw": "正在生成PPT設計...",
        "ja": "PPTデザインを生成中...",
        "nl": "PPT-ontwerp genereren...",
        "fr": "Génération de la conception PPT...",
        "de": "PPT-Design generieren...",
        "es": "Generando el diseño de la presentación...",
        "it": "Generazione del design della presentazione...",
        "ru": "Генерация дизайна презентации..."
    },
    "partner_search": {
        "en": "Searching for partners...",
        "zh": "正在搜索合作伙伴...",
        "zh-tw": "正在搜尋合作夥伴...",
        "ja": "パートナーを検索中...",
        "nl": "Zoeken naar partners...",
        "fr": "Recherche de partenaires...",
        "de": "Suche nach Partnern...",
        "es": "Buscando socios...",
        "it": "Ricerca di partner...",
        "ru": "Поиск партнеров..."
    },
    "completed": {
        "en": "BP generation completed successfully",
        "zh": "商业计划书生成成功",
        "zh-tw": "商業計劃書生成成功",
        "ja": "ビジネスプラン生成が正常に完了しました",
        "nl": "BP-generatie succesvol voltooid",
        "fr": "Génération du plan d'affaires terminée avec succès",
        "de": "BP-Generierung erfolgreich abgeschlossen",
        "es": "Generación del plan de negocio completada con éxito",
        "it": "Generazione del piano aziendale completata con successo",
        "ru": "Генерация бизнес-плана успешно завершена"
    },
    "input_check_failed": {
        "en": "Input completeness check failed",
        "zh": "输入完整性检查失败",
        "zh-tw": "輸入完整性檢查失敗",
        "ja": "入力完全性チェックに失敗しました",
        "nl": "Invoer volledigheid controle mislukt",
        "fr": "Échec de la vérification de l'exhaustivité de la saisie",
        "de": "Eingabevollständigkeitsprüfung fehlgeschlagen",
        "es": "Verificación de la integridad de la entrada fallida",
        "it": "Verifica della completezza dell'input fallita",
        "ru": "Проверка полноты ввода не прошла"
    },
    "generation_failed": {
        "en": "BP generation failed",
        "zh": "商业计划书生成失败",
        "zh-tw": "商業計劃書生成失敗",
        "ja": "ビジネスプラン生成に失敗しました",
        "nl": "BP-generatie mislukt",
        "fr": "Échec de la génération du plan d'affaires",
        "de": "BP-Generierung fehlgeschlagen",
        "es": "Generación del plan de negocio fallida",
        "it": "Generazione del piano aziendale fallita",
        "ru": "Генерация бизнес-плана не удалась"
    },
}


def detect_language(text: str) -> str:
    """
    从文本中检测语言。返回语言代码: 'en', 'zh' (简体), 'zh-tw' (繁体),
    'ja', 'nl', 'fr', 'de', 'es', 'it', 'ru'，默认为 'en'。

    Args:
        text: 要检测语言的输入文本

    Returns:
        语言代码: 'en', 'zh', 'zh-tw', 'ja', 'nl', 'fr', 'de', 'es', 'it', 'ru'
    """
    if not text or not text.strip():
        return 'en'

    text = text.strip()

    # 中文字符: \u4e00-\u9fff
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))

    # 日文字符: 平假名 \u3040-\u309f, 片假名 \u30a0-\u30ff
    # 日文有独特的平假名/片假名，可以区分
    hiragana_chars = len(re.findall(r'[\u3040-\u309f]', text))
    katakana_chars = len(re.findall(r'[\u30a0-\u30ff]', text))
    japanese_chars = hiragana_chars + katakana_chars

    # 俄文字符: 西里尔字母 \u0400-\u04ff
    russian_chars = len(re.findall(r'[\u0400-\u04ff]', text))

    # 计算总字符数用于比例计算
    total_chars = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\u0400-\u04ff\w]', text))

    if total_chars == 0:
        return 'en'

    # 优先检测顺序: 日语（有独特字符）> 俄语（西里尔文）> 中文 > 欧洲语言 > 英语
    if japanese_chars > 0:
        return 'ja'

    # 俄语检测（西里尔文）
    russian_ratio = russian_chars / total_chars if total_chars > 0 else 0
    if russian_ratio > 0.3:
        return 'ru'

    chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
    if chinese_ratio > 0.3:
        # 区分简体和繁体中文
        traditional_patterns = [
            '繁體', '系統', '資訊', '網路', '數據', '企業', '產品', '專業', '應用',
            '計畫', '評估', '設計', '優化', '搜尋', '檢查', '輸入', '開始', '失敗',
            '商業', '投資', '合作', '夥伴', '狀態', '更新', '回調', '成功'
        ]
        traditional_score = sum(1 for pattern in traditional_patterns if pattern in text)

        simplified_patterns = [
            '简体', '系统', '信息', '网络', '数据', '企业', '产品', '专业', '应用',
            '计划', '评估', '设计', '优化', '搜索', '检查', '输入', '开始', '失败',
            '商业', '投资', '合作', '伙伴', '状态', '更新', '回调', '成功'
        ]
        simplified_score = sum(1 for pattern in simplified_patterns if pattern in text)

        if traditional_score > simplified_score:
            return 'zh-tw'
        return 'zh'

    # 欧洲语言: 使用常用词和模式
    # 德语常用词
    german_patterns = [
        r'\bder\b', r'\bdie\b', r'\bdas\b', r'\bund\b', r'\bin\b', r'\bist\b', r'\bzur\b',
        r'\bfür\b', r'\bmit\b', r'\bvon\b', r'\bauf\b', r'\bzu\b', r'\bden\b', r'\bdes\b',
        r'\bwerden\b', r'\bsind\b', r'\bhaben\b', r'\bsein\b'
    ]
    german_score = sum(1 for pattern in german_patterns if re.search(pattern, text, re.IGNORECASE))

    # 西班牙语常用词
    spanish_patterns = [
        r'\bel\b', r'\bla\b', r'\blos\b', r'\blas\b', r'\bde\b', r'\bque\b', r'\by\b',
        r'\ba\b', r'\ben\b', r'\bun\b', r'\buna\b', r'\bes\b', r'\bcon\b', r'\bpor\b',
        r'\bpara\b', r'\bser\b', r'\bhaber\b', r'\bestar\b'
    ]
    spanish_score = sum(1 for pattern in spanish_patterns if re.search(pattern, text, re.IGNORECASE))

    # 意大利语常用词
    italian_patterns = [
        r'\bil\b', r'\bla\b', r'\blo\b', r'\bli\b', r'\ble\b', r'\bdi\b', r'\bche\b',
        r'\be\b', r'\ba\b', r'\bin\b', r'\bun\b', r'\buna\b', r'\bè\b', r'\bcon\b',
        r'\bper\b', r'\bessere\b', r'\bavere\b', r'\bfare\b'
    ]
    italian_score = sum(1 for pattern in italian_patterns if re.search(pattern, text, re.IGNORECASE))

    # 法语常用词
    french_patterns = [
        r'\ble\b', r'\bla\b', r'\bles\b', r'\bde\b', r'\bet\b', r'\bun\b', r'\bune\b',
        r'\bdans\b', r'\bqui\b', r'\bque\b', r'\bà\b', r'\bavec\b', r'\bêtre\b', r'\bavoir\b'
    ]
    french_score = sum(1 for pattern in french_patterns if re.search(pattern, text, re.IGNORECASE))

    # 荷兰语常用词 - 包含更多特定的荷兰语词汇
    dutch_patterns = [
        # 常用荷兰语词
        r'\bde\b', r'\bhet\b', r'\ben\b', r'\bvan\b', r'\bin\b', r'\bis\b', r'\bdat\b',
        r'\bop\b', r'\bvoor\b', r'\bmet\b', r'\bte\b', r'\bzijn\b', r'\bhebben\b', r'\bier\b',
        # 更具体的荷兰语词
        r'\bdie\b', r'\bwat\b', r'\bwie\b', r'\bwaar\b', r'\bwanneer\b', r'\bwaarom\b', r'\bhoe\b',
        # 荷兰语特定的复合词和动词
        r'\baangedreven\b', r'\bonderwijsplatform\b', r'\bstudenten\b', r'\bgepersonaliseerde\b',
        r'\bleerpadaanbevelingen\b', r'\bbiedt\b', r'\bworden\b', r'\bgeworden\b', r'\bgeweest\b'
    ]
    dutch_score = sum(1 for pattern in dutch_patterns if re.search(pattern, text, re.IGNORECASE))

    # 找到得分最高的语言
    lang_scores = {
        'de': german_score,
        'es': spanish_score,
        'it': italian_score,
        'fr': french_score,
        'nl': dutch_score
    }

    # 按得分排序（降序）
    sorted_langs = sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)

    # 如果有明显的赢家（得分>=2且比第二名高至少2分）
    if len(sorted_langs) >= 2:
        best_lang, best_score = sorted_langs[0]
        second_score = sorted_langs[1][1] if len(sorted_langs) > 1 else 0

        # 如果最高分>=2且显著高于第二名，使用它
        if best_score >= 2 and (best_score - second_score) >= 2:
            return best_lang
        # 如果最高分>=3，即使第二名接近也使用它
        elif best_score >= 3:
            return best_lang

    # 如果没有明显赢家但有得分>=2，使用最高分的
    if sorted_langs and sorted_langs[0][1] >= 2:
        return sorted_langs[0][0]

    # 默认返回英语
    return 'en'


def translate_status_message(user_input: str, english_message_key: str) -> str:
    """
    根据用户输入语言获取翻译的状态消息。

    Args:
        user_input: 用户的商业创意（用于检测语言）
        english_message_key: 消息键（在 STATUS_TRANSLATIONS 字典中）

    Returns:
        用户语言的翻译消息，如果未找到则返回英语
    """
    # 检测语言
    lang = detect_language(user_input)

    # 获取翻译，使用回退链: detected_lang -> zh (如果 zh-tw 不可用) -> en
    translations = STATUS_TRANSLATIONS.get(english_message_key, {})

    # 首先尝试检测到的语言
    if lang in translations:
        return translations[lang]

    # 如果检测到 zh-tw 但不可用，回退到 zh
    if lang == 'zh-tw' and 'zh' in translations:
        return translations['zh']

    # 最终回退到英语
    return translations.get("en", english_message_key)
