"""Map clusters to predefined themes using deterministic + LLM approach."""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader

from src.shared.llm_client import get_llm_client
from .cluster_labeler import ClusterLabel
from src.phase2_classification.clustering.representatives import Representative

logger = logging.getLogger(__name__)


@dataclass
class ThemeMapping:
    """Mapping result for a cluster."""
    cluster_id: int
    theme_id: str  # One of the 5 themes, "MULTI", or "UNMAPPED"
    theme_name: str
    confidence: float
    mapping_method: str  # 'deterministic' or 'llm'
    reasoning: Optional[str] = None


class ThemeMapper:
    """
    Map cluster labels to predefined themes.
    
    Strategy:
    1. Try deterministic keyword matching first (fast, no LLM call)
    2. Fall back to LLM for ambiguous cases
    3. Mark low-confidence mappings as UNMAPPED
    """
    
    UNMAPPED_THEME = {
        "id": "UNMAPPED",
        "name": "Unmapped/Other",
        "description": "Reviews that don't fit predefined themes"
    }
    
    MULTI_THEME = {
        "id": "MULTI",
        "name": "Multiple Themes",
        "description": "Reviews spanning multiple themes equally"
    }
    
    def __init__(
        self,
        themes_path: str = "config/themes.json",
        template_path: str = "templates/prompts",
        confidence_threshold: float = 0.6,
        use_llm_fallback: bool = True
    ):
        """
        Initialize theme mapper.
        
        Args:
            themes_path: Path to themes configuration
            template_path: Path to Jinja2 templates
            confidence_threshold: Minimum confidence for valid mapping
            use_llm_fallback: Whether to use LLM for ambiguous cases
        """
        self.confidence_threshold = confidence_threshold
        self.use_llm_fallback = use_llm_fallback
        
        # Load themes
        self.themes = self._load_themes(themes_path)
        self.theme_keywords = self._build_keyword_index()
        
        # Setup LLM (lazy init)
        self._llm_client = None
        self._template = None
        self._template_path = template_path
        
        logger.info(
            f"ThemeMapper initialized with {len(self.themes)} themes, "
            f"confidence_threshold={confidence_threshold}"
        )
    
    def _load_themes(self, path: str) -> List[Dict]:
        """Load theme definitions from JSON config."""
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get("themes", [])
    
    def _build_keyword_index(self) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build keyword -> theme mapping with weights.
        
        Returns:
            Dict mapping keyword -> list of (theme_id, weight) tuples
        """
        keyword_index = {}
        
        for theme in self.themes:
            theme_id = theme["id"]
            keywords = theme.get("keywords", [])
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in keyword_index:
                    keyword_index[keyword_lower] = []
                # Weight by specificity (longer keywords are more specific)
                weight = min(1.0, len(keyword_lower) / 10)
                keyword_index[keyword_lower].append((theme_id, weight))
        
        return keyword_index
    
    def _get_llm_client(self):
        """Lazy init LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client
    
    def _get_template(self):
        """Lazy init template."""
        if self._template is None:
            env = Environment(loader=FileSystemLoader(self._template_path))
            self._template = env.get_template("cluster_theme_map.j2")
        return self._template
    
    def map_deterministic(
        self,
        cluster_label: ClusterLabel,
        representatives: Optional[List[Representative]] = None
    ) -> Optional[ThemeMapping]:
        """
        Try to map cluster to theme using keyword matching.
        
        Args:
            cluster_label: Cluster label with label, summary, key_issues
            representatives: Optional list of representative reviews (for better matching)
        
        Returns:
            ThemeMapping if confident match found, None otherwise
        """
        # Combine all text for matching
        text_parts = [
            cluster_label.label,
            cluster_label.summary,
            " ".join(cluster_label.key_issues)
        ]
        
        # Also include representative review texts for better keyword detection
        if representatives:
            for rep in representatives[:3]:  # Use top 3 representatives
                text_parts.append(rep.text)
        
        text = " ".join(text_parts).lower()
        
        # Count keyword matches per theme
        theme_scores = {theme["id"]: 0.0 for theme in self.themes}
        
        for keyword, theme_weights in self.theme_keywords.items():
            # Check if keyword appears in text
            if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                for theme_id, weight in theme_weights:
                    theme_scores[theme_id] += weight
        
        # Find best theme
        if not any(theme_scores.values()):
            return None
        
        best_theme_id = max(theme_scores, key=theme_scores.get)
        best_score = theme_scores[best_theme_id]
        
        # Calculate confidence based on score differential
        scores_sorted = sorted(theme_scores.values(), reverse=True)
        if len(scores_sorted) > 1 and scores_sorted[0] > 0:
            # Confidence based on how much better the top score is
            differential = (scores_sorted[0] - scores_sorted[1]) / scores_sorted[0]
            confidence = min(0.95, 0.5 + differential * 0.5)
        else:
            confidence = 0.5 if best_score > 0 else 0.0
        
        if confidence < self.confidence_threshold:
            return None
        
        # Get theme name
        theme = next((t for t in self.themes if t["id"] == best_theme_id), None)
        theme_name = theme["name"] if theme else best_theme_id
        
        return ThemeMapping(
            cluster_id=cluster_label.cluster_id,
            theme_id=best_theme_id,
            theme_name=theme_name,
            confidence=confidence,
            mapping_method="deterministic",
            reasoning=f"Keyword match score: {best_score:.2f}"
        )
    
    def map_with_llm(
        self,
        cluster_label: ClusterLabel,
        representatives: Optional[List[Representative]] = None
    ) -> ThemeMapping:
        """
        Map cluster to theme using LLM.
        
        Args:
            cluster_label: Cluster label with label, summary, key_issues
        
        Returns:
            ThemeMapping from LLM response
        """
        template = self._get_template()
        llm_client = self._get_llm_client()
        
        # Include representative texts in prompt for better context
        rep_texts = []
        if representatives:
            for rep in representatives[:3]:  # Top 3 representatives
                rep_texts.append({
                    "text": rep.text[:300],  # Truncate for prompt size
                    "helpful_count": rep.helpful_count
                })
        
        # Render prompt
        prompt = template.render(
            cluster_id=cluster_label.cluster_id,
            cluster_label=cluster_label.label,
            cluster_summary=cluster_label.summary,
            key_issues=cluster_label.key_issues,
            representative_texts=rep_texts,
            themes=self.themes
        )
        
        system_prompt = """You are an expert at categorizing app review clusters.
Map each cluster to exactly one predefined theme.
Always respond with valid JSON only."""
        
        try:
            result = llm_client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                use_case="classification"
            )
            
            theme_id = result.get("theme_id", "UNMAPPED")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            # Validate theme_id
            valid_ids = [t["id"] for t in self.themes] + ["MULTI", "UNMAPPED"]
            if theme_id not in valid_ids:
                logger.warning(f"Invalid theme_id from LLM: {theme_id}, using UNMAPPED")
                theme_id = "UNMAPPED"
            
            # Get theme name
            if theme_id == "UNMAPPED":
                theme_name = self.UNMAPPED_THEME["name"]
            elif theme_id == "MULTI":
                theme_name = self.MULTI_THEME["name"]
            else:
                theme = next((t for t in self.themes if t["id"] == theme_id), None)
                theme_name = theme["name"] if theme else theme_id
            
            # Apply confidence threshold
            if confidence < self.confidence_threshold and theme_id not in ["UNMAPPED", "MULTI"]:
                logger.info(
                    f"Cluster {cluster_label.cluster_id}: Low confidence ({confidence:.2f}), "
                    f"marking as UNMAPPED"
                )
                theme_id = "UNMAPPED"
                theme_name = self.UNMAPPED_THEME["name"]
            
            return ThemeMapping(
                cluster_id=cluster_label.cluster_id,
                theme_id=theme_id,
                theme_name=theme_name,
                confidence=confidence,
                mapping_method="llm",
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"LLM mapping failed for cluster {cluster_label.cluster_id}: {e}")
            return ThemeMapping(
                cluster_id=cluster_label.cluster_id,
                theme_id="UNMAPPED",
                theme_name=self.UNMAPPED_THEME["name"],
                confidence=0.0,
                mapping_method="llm_failed",
                reasoning=str(e)
            )
    
    def map_cluster(
        self, 
        cluster_label: ClusterLabel,
        representatives: Optional[List[Representative]] = None,
        cluster_size: Optional[int] = None
    ) -> ThemeMapping:
        """
        Map a single cluster to a theme.
        
        Args:
            cluster_label: Cluster label from labeler
            representatives: Optional list of representative reviews
            cluster_size: Optional cluster size (large clusters may need LLM)
        
        Returns:
            ThemeMapping result, for large clusters (>20 reviews), prefer LLM
        """
        # For large clusters, prefer LLM as they may contain mixed themes
        use_llm_preferred = cluster_size and cluster_size > 20
        
        if not use_llm_preferred:
            # Try deterministic first (now with representative texts)
            deterministic_result = self.map_deterministic(cluster_label, representatives)
            
            if deterministic_result:
                logger.debug(
                    f"Cluster {cluster_label.cluster_id}: "
                    f"Deterministic match -> {deterministic_result.theme_id}"
                )
                return deterministic_result
        
        # Use LLM for large clusters or if no deterministic match
        if self.use_llm_fallback:
            if use_llm_preferred:
                logger.debug(
                    f"Cluster {cluster_label.cluster_id}: "
                    f"Large cluster ({cluster_size} reviews), using LLM for better accuracy"
                )
            else:
                logger.debug(
                    f"Cluster {cluster_label.cluster_id}: "
                    f"No deterministic match, using LLM"
                )
            return self.map_with_llm(cluster_label, representatives)
        
        # No LLM fallback - return UNMAPPED
        return ThemeMapping(
            cluster_id=cluster_label.cluster_id,
            theme_id="UNMAPPED",
            theme_name=self.UNMAPPED_THEME["name"],
            confidence=0.0,
            mapping_method="no_match",
            reasoning="No keyword match and LLM fallback disabled"
        )
    
    def map_all_clusters(
        self,
        cluster_labels: Dict[int, ClusterLabel],
        cluster_representatives: Optional[Dict[int, List[Representative]]] = None,
        cluster_sizes: Optional[Dict[int, int]] = None
    ) -> Dict[int, ThemeMapping]:
        """
        Map all clusters to themes.
        
        Args:
            cluster_labels: Dict mapping cluster_id -> ClusterLabel
            cluster_representatives: Optional dict mapping cluster_id -> representatives
            cluster_sizes: Optional dict mapping cluster_id -> size
        
        Returns:
            Dict mapping cluster_id -> ThemeMapping
        """
        mappings = {}
        deterministic_count = 0
        llm_count = 0
        
        logger.info(f"Mapping {len(cluster_labels)} clusters to themes...")
        
        for cluster_id, label in sorted(cluster_labels.items()):
            # Get representatives and size for this cluster if available
            reps = cluster_representatives.get(cluster_id) if cluster_representatives else None
            size = cluster_sizes.get(cluster_id) if cluster_sizes else None
            
            mapping = self.map_cluster(label, representatives=reps, cluster_size=size)
            mappings[cluster_id] = mapping
            
            if mapping.mapping_method == "deterministic":
                deterministic_count += 1
            elif mapping.mapping_method == "llm":
                llm_count += 1
        
        logger.info(
            f"Mapping complete: {deterministic_count} deterministic, "
            f"{llm_count} LLM, "
            f"{len(cluster_labels) - deterministic_count - llm_count} other"
        )
        
        # Log theme distribution
        theme_dist = {}
        for mapping in mappings.values():
            theme_dist[mapping.theme_id] = theme_dist.get(mapping.theme_id, 0) + 1
        logger.info(f"Theme distribution: {theme_dist}")
        
        return mappings

