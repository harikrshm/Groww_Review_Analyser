"""Graph generation for Phase 3 reports."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

logger = logging.getLogger(__name__)

class GraphGenerator:
    """
    Generate static graphs for email reports.
    """
    
    def __init__(self, output_dir: str = "data/reports/graphs"):
        """Initialize graph generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Style settings
        plt.style.use('seaborn-v0_8-white')
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'sans-serif']
        plt.rcParams['axes.spines.left'] = False
        plt.rcParams['axes.spines.right'] = False
        plt.rcParams['axes.spines.top'] = False
        plt.rcParams['axes.spines.bottom'] = True
        plt.rcParams['text.color'] = '#334155'
        plt.rcParams['xtick.color'] = '#64748B'
        plt.rcParams['ytick.color'] = '#64748B'
        
        self.colors = {
            "pos": "#10B981",  # Emerald
            "neg": "#F87171",  # Rose
            "neu": "#94A3B8",  # Slate
            "bar_text": "#1E293B"
        }
        
    def generate_sentiment_balance_chart(
        self, 
        data: pd.DataFrame, 
        filename: str = "sentiment_balance.png",
        is_insight_based: bool = False
    ) -> Path:
        """
        Generate Diverging Bar Chart: Positive vs Negative per Theme.
        Large, clear visualization showing sentiment for all themes.
        
        Args:
            data: DataFrame with theme_id, sentiment (or rating), and count columns
            filename: Output filename
            is_insight_based: If True, data contains insights with sentiment field. 
                            If False, data contains reviews with rating field.
        """
        try:
            df = data.copy()
            
            # Handle both review-based (rating) and insight-based (sentiment) data
            if is_insight_based:
                # For insights, sentiment is already present
                df['sentiment'] = df['sentiment'].str.capitalize()
                # Map to standard labels
                df['sentiment'] = df['sentiment'].map({
                    'Positive': 'Positive',
                    'Negative': 'Negative',
                    'Neutral': 'Neutral'
                }).fillna('Neutral')
            else:
                # For reviews, derive sentiment from rating
                df['sentiment'] = pd.cut(
                    df['rating'], 
                    bins=[0, 2, 3, 5], 
                    labels=['Negative', 'Neutral', 'Positive']
                )
            
            pivot = df.pivot_table(
                index='theme_id', 
                columns='sentiment', 
                values='count', 
                aggfunc='sum', 
                fill_value=0
            )
            
            # Ensure all sentiment columns exist
            for sentiment in ['Negative', 'Neutral', 'Positive']:
                if sentiment not in pivot.columns:
                    pivot[sentiment] = 0
            
            pivot['Total'] = pivot['Negative'] + pivot['Positive'] + pivot.get('Neutral', 0)
            pivot = pivot.sort_values('Total', ascending=True)
            
            themes = pivot.index
            positives = pivot['Positive']
            negatives = -pivot['Negative'] 
            
            # Much larger figure for clarity with more height for spacing
            fig, ax = plt.subplots(figsize=(14, 8), dpi=150)
            
            # Bars with more spacing (reduce height to create gaps)
            bar_height = 0.5
            ax.barh(themes, negatives, color=self.colors['neg'], label='Negative', height=bar_height)
            ax.barh(themes, positives, color=self.colors['pos'], label='Positive', height=bar_height)
            
            ax.axvline(0, color='#E2E8F0', linewidth=2)
            
            # Intelligent label placement with larger fonts and better spacing
            max_val = max(pivot['Negative'].max() if pivot['Negative'].max() > 0 else 1, 
                         pivot['Positive'].max() if pivot['Positive'].max() > 0 else 1)
            offset = max(max_val * 0.08, 2)  # Minimum 2 units offset
            
            for i, (neg, pos) in enumerate(zip(pivot['Negative'], pivot['Positive'])):
                # Negative labels - always place outside to avoid overlap
                if neg > 0:
                    label_x = -neg - offset
                    ax.text(label_x, i, str(int(neg)), va='center', ha='right', 
                           fontsize=12, color=self.colors['neg'], fontweight='bold')
                
                # Positive labels - always place outside to avoid overlap
                if pos > 0:
                    label_x = pos + offset
                    ax.text(label_x, i, str(int(pos)), va='center', ha='left', 
                           fontsize=12, color=self.colors['pos'], fontweight='bold')
            
            count_label = "Insight Count" if is_insight_based else "Review Count"
            ax.set_title("Sentiment Balance by Theme", fontsize=18, fontweight='bold', loc='left', pad=25)
            ax.set_xlabel(f"{count_label} (Negative ← | → Positive)", fontsize=14, color='#64748B', fontweight='500', labelpad=10)
            
            # Set x-axis limits to accommodate labels
            x_min = -max(pivot['Negative'].max() * 1.25, 10)
            x_max = max(pivot['Positive'].max() * 1.25, 10)
            ax.set_xlim(x_min, x_max)
            
            ticks = ax.get_xticks()
            ax.set_xticklabels([str(int(abs(x))) for x in ticks], fontsize=12)
            
            # Larger, clearer theme labels with more space
            theme_labels = [t.replace('_', ' ').title() for t in themes]
            ax.set_yticks(range(len(themes)))
            ax.set_yticklabels(theme_labels, fontsize=13, fontweight='600')
            
            ax.grid(False)
            # Legend removed as requested
            
            # Better margins - more left space for theme labels, less bottom space needed without legend
            plt.subplots_adjust(left=0.35, right=0.92, top=0.90, bottom=0.15)
            
            output_path = self.output_dir / filename
            plt.savefig(output_path, bbox_inches='tight', pad_inches=0.3, dpi=150)
            plt.close(fig)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate sentiment chart: {e}")
            raise

    def generate_theme_drilldown_chart(
        self, 
        clusters_report: Dict,
        theme_id: str,
        theme_name: str,
        filename: str = "theme_drilldown.png",
        is_insight_based: bool = False
    ) -> Path:
        """
        Generate Horizontal Bar Chart: Specific issues within the most negative theme.
        This is a drill-down from Graph 1 - shows what specific problems exist within the problematic theme.
        
        Args:
            clusters_report: Dictionary containing cluster data
            theme_id: Theme ID to drill down into
            theme_name: Display name for the theme
            filename: Output filename
            is_insight_based: If True, uses insight_clusters. If False, uses clusters.
        """
        try:
            # Get clusters based on clustering type
            if is_insight_based:
                clusters = clusters_report.get("insight_clusters", [])
            else:
                clusters = clusters_report.get("clusters", [])
            
            # Filter clusters for the specified theme and negative sentiment
            theme_clusters = []
            for c in clusters:
                if c.get('theme_id') != theme_id or c.get('theme_id') == 'UNMAPPED':
                    continue
                
                # Check for negative sentiment
                is_negative = False
                if is_insight_based:
                    # For insights, check sentiment field directly
                    is_negative = c.get('sentiment', '').lower() == 'negative'
                else:
                    # For reviews, check avg_rating
                    is_negative = c.get('avg_rating', 5) < 3.5
                
                if is_negative:
                    theme_clusters.append({
                        'label': c.get('label', 'Unknown Issue'),
                        'size': c.get('size', 0),
                        'avg_rating': c.get('avg_rating', 3) if not is_insight_based else None
                    })
            
            if not theme_clusters:
                # Fallback: show all negative clusters if theme-specific ones not found
                logger.warning(f"No negative clusters found for theme {theme_id}, showing all negative clusters")
                for c in clusters:
                    is_negative = False
                    if is_insight_based:
                        is_negative = c.get('sentiment', '').lower() == 'negative'
                    else:
                        is_negative = c.get('avg_rating', 5) < 3.5
                    
                    if is_negative and c.get('theme_id') != 'UNMAPPED':
                        theme_clusters.append({
                            'label': c.get('label', 'Unknown Issue'),
                            'size': c.get('size', 0),
                            'avg_rating': c.get('avg_rating', 3) if not is_insight_based else None
                        })
            
            df = pd.DataFrame(theme_clusters)
            if df.empty:
                return self._create_empty_chart(filename, f"No Issues Found in {theme_name}")
            
            # Sort by size (most impactful issues first) and take top 5-7
            df = df.sort_values('size', ascending=True).tail(7)
            
            fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
            
            bars = ax.barh(df['label'], df['size'], color=self.colors['neg'], height=0.5, alpha=0.9)
            
            # Intelligent label placement
            max_val = df['size'].max()
            offset = max_val * 0.02
            
            for bar in bars:
                width = bar.get_width()
                # If bar is wide enough, label inside
                if width > max_val * 0.15:
                    ax.text(width - offset, bar.get_y() + bar.get_height()/2, 
                           str(int(width)), va='center', ha='right',
                           fontsize=9, fontweight='bold', color='white')
                else:
                    ax.text(width + offset, bar.get_y() + bar.get_height()/2, 
                           str(int(width)), va='center', ha='left',
                           fontsize=9, fontweight='bold', color=self.colors['neg'])
            
            # Title shows which theme we're drilling into
            theme_display = theme_name.replace('_', ' ').title()
            ax.set_title(f"Top Issues in {theme_display}", fontsize=12, fontweight='bold', loc='left', pad=15)
            count_label = "Number of Insights" if is_insight_based else "Number of Reviews"
            ax.set_xlabel(count_label, fontsize=10, color='#64748B')
            
            # Wrap labels
            labels = [self._wrap_label(l, max_len=40) for l in df['label']]
            ax.set_yticklabels(labels, fontsize=10)
            
            ax.grid(axis='x', alpha=0.3, linestyle='--')
            
            plt.subplots_adjust(left=0.4, right=0.95, top=0.9, bottom=0.15)
            
            output_path = self.output_dir / filename
            plt.savefig(output_path, bbox_inches='tight', pad_inches=0.2)
            plt.close(fig)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate theme drilldown chart: {e}")
            raise

    def _wrap_label(self, label: str, max_len: int = 35) -> str:
        """Truncate or wrap long labels."""
        if len(label) > max_len:
            return label[:max_len] + "..."
        return label

    def _create_empty_chart(self, filename: str, message: str) -> Path:
        """Generate a placeholder image."""
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, message, ha='center', va='center')
        ax.axis('off')
        output_path = self.output_dir / filename
        plt.savefig(output_path)
        plt.close(fig)
        return output_path
