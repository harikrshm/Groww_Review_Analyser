"""LLM-based cluster labeling and summarization."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from src.shared.llm_client import get_llm_client
from src.phase2_classification.clustering.representatives import Representative

logger = logging.getLogger(__name__)


@dataclass
class ClusterLabel:
    """Label and summary for a cluster."""
    cluster_id: int
    label: str
    summary: str
    key_issues: List[str]
    llm_response_raw: Optional[str] = None


class ClusterLabeler:
    """
    Generate labels and summaries for clusters using LLM.
    
    Uses representative reviews to label each cluster with a single LLM call.
    """
    
    def __init__(self, template_path: str = "templates/prompts"):
        """
        Initialize cluster labeler.
        
        Args:
            template_path: Path to Jinja2 templates directory
        """
        self.llm_client = get_llm_client()
        
        # Setup Jinja2 environment
        template_dir = Path(template_path)
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("cluster_label.j2")
        
        logger.info("ClusterLabeler initialized")
    
    def label_cluster(
        self,
        cluster_id: int,
        representatives: List[Representative]
    ) -> ClusterLabel:
        """
        Generate label and summary for a cluster.
        
        Args:
            cluster_id: Cluster identifier
            representatives: List of representative reviews
        
        Returns:
            ClusterLabel with label, summary, and key issues
        """
        if not representatives:
            return ClusterLabel(
                cluster_id=cluster_id,
                label="Empty Cluster",
                summary="No representative reviews available.",
                key_issues=[]
            )
        
        # Render prompt template
        prompt = self.template.render(
            cluster_id=cluster_id,
            representatives=representatives
        )
        
        # System prompt
        system_prompt = """You are an expert at analyzing and categorizing app store reviews.
Your task is to identify the common theme in a cluster of similar reviews and provide a concise label and summary.
Always respond with valid JSON only."""
        
        try:
            # Get LLM response
            result = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                use_case="classification"
            )
            
            return ClusterLabel(
                cluster_id=cluster_id,
                label=result.get("label", "Unknown"),
                summary=result.get("summary", ""),
                key_issues=result.get("key_issues", [])
            )
            
        except Exception as e:
            logger.error(f"Failed to label cluster {cluster_id}: {e}")
            # Return fallback label based on first representative
            fallback_label = "Review Cluster"
            if representatives:
                # Extract first few words from first representative
                first_text = representatives[0].text[:50]
                fallback_label = f"Reviews about: {first_text}..."
            
            return ClusterLabel(
                cluster_id=cluster_id,
                label=fallback_label,
                summary=f"Cluster of {len(representatives)} similar reviews (labeling failed)",
                key_issues=[]
            )
    
    def label_all_clusters(
        self,
        cluster_representatives: Dict[int, List[Representative]]
    ) -> Dict[int, ClusterLabel]:
        """
        Label all clusters.
        
        Args:
            cluster_representatives: Dict mapping cluster_id -> representatives
        
        Returns:
            Dict mapping cluster_id -> ClusterLabel
        """
        labels = {}
        total = len(cluster_representatives)
        
        logger.info(f"Labeling {total} clusters...")
        
        for i, (cluster_id, representatives) in enumerate(
            sorted(cluster_representatives.items()), 1
        ):
            logger.info(f"Labeling cluster {cluster_id} ({i}/{total})...")
            labels[cluster_id] = self.label_cluster(cluster_id, representatives)
            logger.debug(f"  Label: {labels[cluster_id].label}")
        
        logger.info(f"Labeled {len(labels)} clusters")
        return labels

