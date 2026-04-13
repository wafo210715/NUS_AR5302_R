#!/usr/bin/env python3
"""
Tesco Store Distribution & Dietary Patterns Analysis

Research Question: To what extent do Tesco store characteristics (type, diversity)
versus area deprivation (IMD) explain spatial variation in food purchasing patterns
across London?

This script:
1. Loads grocery, IMD, and Tesco POI data
2. Performs spatial aggregation of store data to LSOA level
3. Runs PCA on food categories to extract dietary patterns
4. Runs regression models comparing store metrics vs IMD effects
5. Generates visualizations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')

# Spatial analysis
try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    print("Warning: geopandas not installed. Spatial visualizations will be limited.")

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_TESCO = PROJECT_ROOT / "tesco-data" / "7796666"
DATA_HEALTH = PROJECT_ROOT / "tesco-data" / "7796672"
OUTPUT_DIR = PROJECT_ROOT / "output"

# LSOA 2011 boundaries (downloaded by 01_acquire_data.py)
LSOA_SHP_PATH = DATA_RAW / "LSOA_2011" / "LSOA_2011_EW_BGC_V3.shp"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configure plotting style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14

# Food categories for PCA (based on the paper - 12 categories used)
# From the original paper: beer, dairy, eggs, fats_oils, fish, fruit_veg, grains,
# meat_red, poultry, readymade, soft_drinks, sweets, wine (alcohol categories combined)
FOOD_CATEGORIES = [
    'f_beer', 'f_dairy', 'f_eggs', 'f_fats_oils', 'f_fish', 'f_fruit_veg',
    'f_grains', 'f_meat_red', 'f_poultry', 'f_readymade', 'f_soft_drinks',
    'f_spirits', 'f_sweets', 'f_tea_coffee', 'f_water', 'f_wine'
]

# 12 categories used in the paper (alcohol combined, tea_coffee and water excluded)
FOOD_CATEGORIES_PAPER = [
    'f_beer', 'f_dairy', 'f_eggs', 'f_fats_oils', 'f_fish', 'f_fruit_veg',
    'f_grains', 'f_meat_red', 'f_poultry', 'f_readymade', 'f_soft_drinks',
    'f_sweets', 'f_wine'  # Note: paper combined alcohol, we keep separate for now
]


def load_grocery_data():
    """Load LSOA-level grocery data"""
    print("Loading grocery data...")
    df = pd.read_csv(DATA_TESCO / "year_lsoa_grocery.csv")
    print(f"  Loaded {len(df)} LSOAs with {len(df.columns)} variables")
    return df


def load_imd_data():
    """Load IMD 2015 data"""
    print("Loading IMD 2015 data...")
    df = pd.read_excel(DATA_RAW / "IMD_2015_File_1_Index.xlsx", sheet_name='IMD 2015')

    # Rename key columns (exact column names from the Excel file)
    rename_dict = {
        'LSOA code (2011)': 'lsoa_code',
        'LSOA name (2011)': 'lsoa_name',
        'Local Authority District code (2013)': 'lad_code',
        'Local Authority District name (2013)': 'lad_name',
        'Index of Multiple Deprivation (IMD) Rank (where 1 is most deprived)': 'imd_rank',
        'Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)': 'imd_decile',
    }
    df = df.rename(columns=rename_dict)

    print(f"  Loaded {len(df)} LSOAs with IMD data")
    return df


def load_tesco_poi():
    """Load Tesco POI data"""
    print("Loading Tesco POI data...")

    # Try OSM data first, then sample data
    osm_path = DATA_RAW / "tesco_osm_london.csv"
    sample_path = DATA_RAW / "tesco_sample_london.csv"

    if osm_path.exists():
        df = pd.read_csv(osm_path)
        print(f"  Loaded {len(df)} Tesco stores from OSM")
    elif sample_path.exists():
        df = pd.read_csv(sample_path)
        print(f"  Loaded {len(df)} sample Tesco stores")
    else:
        raise FileNotFoundError("No Tesco POI data found")

    return df


def load_postcode_geo():
    """Load postcode to geography mapping"""
    print("Loading postcode-geography mapping...")
    df = pd.read_csv(DATA_HEALTH / "london_pcd2geo_2015.csv")
    print(f"  Loaded {len(df)} postcode mappings")
    return df


def assign_stores_to_lsoa(stores_df, grocery_df, postcode_df):
    """
    Assign Tesco stores to LSOAs using spatial proximity or postcode matching

    For OSM data with coordinates, we use nearest LSOA centroid
    """
    print("Assigning stores to LSOAs...")

    # Calculate LSOA centroids from postcode data
    lsoa_centroids = postcode_df.groupby('lsoa11').agg({
        'lat': 'mean',
        'long': 'mean'
    }).reset_index()
    lsoa_centroids.columns = ['area_id', 'lsoa_lat', 'lsoa_lon']

    # For each store, find nearest LSOA
    from scipy.spatial import cKDTree

    # Build KD-tree for LSOA centroids
    lsoa_coords = lsoa_centroids[['lsoa_lat', 'lsoa_lon']].values
    tree = cKDTree(lsoa_coords)

    # Query nearest LSOA for each store
    store_coords = stores_df[['lat', 'lon']].values
    distances, indices = tree.query(store_coords, k=1)

    # Assign LSOA to stores
    stores_df = stores_df.copy()
    stores_df['assigned_lsoa'] = lsoa_centroids.iloc[indices]['area_id'].values
    stores_df['distance_to_lsoa_km'] = distances * 111  # Approximate km conversion

    print(f"  Assigned stores to LSOAs (mean distance: {stores_df['distance_to_lsoa_km'].mean():.2f} km)")

    return stores_df


def calculate_store_metrics(stores_df, grocery_df):
    """
    Calculate store metrics for each LSOA:
    - Store count
    - Store type counts (Express, Superstore, Extra)
    - Store diversity (Shannon index)
    """
    print("Calculating store metrics per LSOA...")

    # Store counts by type
    store_counts = stores_df.groupby(['assigned_lsoa', 'store_type']).size().unstack(fill_value=0)
    store_counts['total_stores'] = store_counts.sum(axis=1)
    store_counts = store_counts.reset_index()
    store_counts.columns = ['area_id'] + [f'store_{c.lower()}' for c in store_counts.columns[1:-1]] + ['store_total']

    # Calculate store diversity (Shannon index)
    def shannon_diversity(row):
        types = ['express', 'superstore', 'extra', 'metro', 'unknown']
        counts = [row.get(f'store_{t}', 0) for t in types]
        counts = [c for c in counts if c > 0]
        if len(counts) <= 1:
            return 0
        total = sum(counts)
        proportions = [c/total for c in counts]
        return -sum(p * np.log(p) for p in proportions if p > 0)

    store_counts['store_diversity'] = store_counts.apply(shannon_diversity, axis=1)

    # Merge with grocery data
    metrics_df = grocery_df[['area_id']].merge(store_counts, on='area_id', how='left')

    # Fill NA with 0 for LSOAs without stores
    store_cols = [c for c in metrics_df.columns if c.startswith('store_')]
    metrics_df[store_cols] = metrics_df[store_cols].fillna(0)

    print(f"  Store metrics calculated for {len(metrics_df)} LSOAs")
    print(f"  LSOAs with stores: {(metrics_df['store_total'] > 0).sum()}")

    return metrics_df


def run_pca_analysis(grocery_df, food_cols):
    """
    Run PCA on food categories to extract dietary patterns

    Returns:
    - PCA object
    - DataFrame with PC scores
    - Loadings DataFrame
    """
    print("\n" + "=" * 60)
    print("RUNNING PCA ANALYSIS")
    print("=" * 60)

    # Select food columns that exist
    available_cols = [c for c in food_cols if c in grocery_df.columns]
    print(f"Using {len(available_cols)} food categories: {available_cols}")

    # Extract food data
    X = grocery_df[available_cols].copy()

    # Handle any missing values
    X = X.fillna(0)

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Run PCA
    pca = PCA()
    pc_scores = pca.fit_transform(X_scaled)

    # Create DataFrame with PC scores
    pc_df = pd.DataFrame(
        pc_scores[:, :5],  # First 5 PCs
        columns=[f'PC{i+1}' for i in range(5)],
        index=grocery_df.index
    )
    pc_df['area_id'] = grocery_df['area_id'].values

    # Create loadings DataFrame
    loadings = pd.DataFrame(
        pca.components_[:5].T,
        columns=[f'PC{i+1}' for i in range(5)],
        index=available_cols
    )

    # Variance explained
    var_explained = pca.explained_variance_ratio_[:5] * 100

    print(f"\nVariance explained:")
    for i, v in enumerate(var_explained):
        print(f"  PC{i+1}: {v:.1f}%")
    print(f"  Total (PC1+PC2): {var_explained[0] + var_explained[1]:.1f}%")

    # Interpret PCs
    print("\nPC1 (Convenience Pattern) - Top positive loadings:")
    pc1_sorted = loadings['PC1'].sort_values(ascending=False)
    print(pc1_sorted.head(5).to_string())
    print("\nPC1 - Top negative loadings:")
    print(pc1_sorted.tail(5).to_string())

    print("\nPC2 (Variety Pattern) - Top loadings:")
    pc2_sorted = loadings['PC2'].abs().sort_values(ascending=False)
    print(loadings.loc[pc2_sorted.head(5).index, 'PC2'].to_string())

    return pca, pc_df, loadings, var_explained


def merge_all_data(grocery_df, imd_df, store_metrics_df, pc_df):
    """Merge all data sources for regression analysis"""
    print("\nMerging all data sources...")

    # Start with grocery data
    df = grocery_df.copy()

    # Merge IMD data
    imd_subset = imd_df[['lsoa_code', 'imd_rank', 'imd_decile']].copy()
    df = df.merge(imd_subset, left_on='area_id', right_on='lsoa_code', how='left')

    # Merge store metrics
    df = df.merge(store_metrics_df, on='area_id', how='left')

    # Merge PC scores
    df = df.merge(pc_df[['area_id', 'PC1', 'PC2']], on='area_id', how='left')

    # Calculate IMD rank percentile (higher = less deprived)
    df['imd_percentile'] = df['imd_rank'] / df['imd_rank'].max() * 100

    print(f"  Final dataset: {len(df)} LSOAs")

    return df


def load_lsoa_boundaries(london_only=True):
    """
    Load LSOA 2011 boundaries from shapefile

    Args:
        london_only: If True, filter to London LSOAs only (codes starting with E01)

    Returns:
        GeoDataFrame with LSOA boundaries
    """
    if not HAS_GEOPANDAS:
        print("  Warning: geopandas not available, skipping spatial data")
        return None

    if not LSOA_SHP_PATH.exists():
        print(f"  Warning: LSOA shapefile not found at {LSOA_SHP_PATH}")
        print("  Run python/01_acquire_data.py first to download boundaries")
        return None

    print(f"\nLoading LSOA boundaries from {LSOA_SHP_PATH}...")
    gdf = gpd.read_file(LSOA_SHP_PATH)

    print(f"  Loaded {len(gdf)} LSOAs")
    print(f"  CRS: {gdf.crs}")

    # The shapefile uses 'LSOA11CD' as the LSOA code field
    # Rename for consistency with our data
    gdf = gdf.rename(columns={'LSOA11CD': 'lsoa_code'})

    # Filter to London if requested (codes starting with E01)
    if london_only:
        # London LSOA codes start with E0100xxxx
        # Get unique prefixes to understand the data
        london_mask = gdf['lsoa_code'].str.startswith('E01')
        gdf = gdf[london_mask]
        print(f"  Filtered to {len(gdf)} London LSOAs")

    return gdf


def merge_spatial_data(df, lsoa_gdf):
    """
    Merge analysis DataFrame with LSOA geometries

    Args:
        df: Analysis DataFrame with lsoa_code or area_id column
        lsoa_gdf: GeoDataFrame with LSOA boundaries

    Returns:
        GeoDataFrame with all variables + geometry
    """
    if lsoa_gdf is None:
        return None

    # Ensure we have lsoa_code column
    if 'lsoa_code' not in df.columns and 'area_id' in df.columns:
        df = df.copy()
        df['lsoa_code'] = df['area_id']

    # Merge
    gdf = lsoa_gdf.merge(df, on='lsoa_code', how='inner')

    print(f"  Merged spatial data: {len(gdf)} LSOAs with geometry")

    return gdf


def run_regression_analysis(df):
    """
    Run regression models comparing:
    - Model 1: Store metrics only
    - Model 2: IMD only
    - Model 3: Store metrics + IMD
    """
    print("\n" + "=" * 60)
    print("RUNNING REGRESSION ANALYSIS")
    print("=" * 60)

    # Prepare data
    analysis_df = df.dropna(subset=['PC1', 'PC2', 'imd_rank', 'store_total'])
    print(f"Analyzing {len(analysis_df)} LSOAs with complete data")

    results = {}

    for pc in ['PC1', 'PC2']:
        print(f"\n{'='*40}")
        print(f"Dependent Variable: {pc}")
        print('='*40)

        y = analysis_df[pc]

        # Model 1: Store metrics only
        X1 = analysis_df[['store_total', 'store_diversity', 'store_express', 'store_superstore', 'store_extra']]
        X1 = sm.add_constant(X1)
        model1 = sm.OLS(y, X1).fit()

        # Model 2: IMD only
        X2 = analysis_df[['imd_percentile']]
        X2 = sm.add_constant(X2)
        model2 = sm.OLS(y, X2).fit()

        # Model 3: Store metrics + IMD
        X3 = analysis_df[['store_total', 'store_diversity', 'store_express', 'store_superstore', 'store_extra', 'imd_percentile']]
        X3 = sm.add_constant(X3)
        model3 = sm.OLS(y, X3).fit()

        print(f"\nModel 1 (Store metrics only): R² = {model1.rsquared:.4f}")
        print(f"Model 2 (IMD only): R² = {model2.rsquared:.4f}")
        print(f"Model 3 (Store + IMD): R² = {model3.rsquared:.4f}")

        results[pc] = {
            'model1': model1,
            'model2': model2,
            'model3': model3,
            'n': len(analysis_df)
        }

    return results


def create_visualizations(df, pc_df, loadings, var_explained, regression_results):
    """Create the 5 core visualizations"""
    print("\n" + "=" * 60)
    print("CREATING VISUALIZATIONS")
    print("=" * 60)

    # Load LSOA boundaries for spatial visualizations
    lsoa_gdf = load_lsoa_boundaries(london_only=True)
    spatial_df = merge_spatial_data(df, lsoa_gdf) if lsoa_gdf is not None else None

    # Load Tesco store locations for overlay
    tesco_stores = None
    if HAS_GEOPANDAS:
        tesco_path = DATA_RAW / "tesco_osm_london.csv"
        if tesco_path.exists():
            tesco_df = pd.read_csv(tesco_path)
            tesco_stores = gpd.GeoDataFrame(
                tesco_df,
                geometry=gpd.points_from_xy(tesco_df['lon'], tesco_df['lat']),
                crs='EPSG:4326'
            )
            # Convert to British National Grid
            tesco_stores = tesco_stores.to_crs('EPSG:27700')

    # 1. Tesco Store Distribution Map
    print("Creating visualization 1: Store distribution...")
    create_store_distribution_map(df, spatial_df, tesco_stores)

    # 2. IMD vs Store Type Relationship
    print("Creating visualization 2: IMD vs store type...")
    create_imd_store_type_plot(df)

    # 3. PCA Biplot
    print("Creating visualization 3: PCA biplot...")
    create_pca_biplot(loadings, var_explained)

    # 4. Regression Coefficient Forest Plot
    print("Creating visualization 4: Regression coefficients...")
    create_regression_forest_plot(regression_results)

    # 5. PC Scores Spatial Distribution Map
    print("Creating visualization 5: PC scores spatial distribution...")
    create_pc_spatial_map(spatial_df)

    print(f"\nAll visualizations saved to: {OUTPUT_DIR}")


def create_store_distribution_map(df, spatial_df=None, tesco_stores=None):
    """Visualization 1: Tesco store distribution choropleth map"""
    fig, ax = plt.subplots(figsize=(14, 12))

    if spatial_df is not None and HAS_GEOPANDAS:
        # Choropleth map with LSOA boundaries
        # Create categorical bins for store count
        spatial_df = spatial_df.copy()
        spatial_df['store_category'] = pd.cut(
            spatial_df['store_total'],
            bins=[-1, 0, 1, 2, 100],
            labels=['0 stores', '1 store', '2 stores', '3+ stores']
        )

        # Plot LSOAs colored by store count
        spatial_df.plot(
            column='store_category',
            cmap='YlOrRd',
            legend=True,
            ax=ax,
            edgecolor='none',
            alpha=0.8,
            missing_kwds={'color': 'lightgrey', 'label': 'No data'}
        )

        # Overlay store locations
        if tesco_stores is not None and len(tesco_stores) > 0:
            tesco_stores.plot(
                ax=ax,
                color='blue',
                markersize=8,
                alpha=0.6,
                label='Tesco stores'
            )
            ax.legend(loc='upper left', fontsize=10)

        ax.set_title('Tesco Store Distribution Across London LSOAs', fontsize=14, fontweight='bold')
        ax.set_axis_off()

        # Add scale bar and north arrow (simplified)
        ax.annotate('N', xy=(0.95, 0.95), xycoords='axes fraction', fontsize=16, fontweight='bold')

    else:
        # Fallback: Simple scatter plot (without proper boundaries)
        print("  Note: Using fallback visualization (no spatial data available)")
        scatter = ax.scatter(
            df['area_sq_km'],
            df['people_per_sq_km'],
            c=df['store_total'],
            cmap='YlOrRd',
            alpha=0.5,
            s=10
        )
        plt.colorbar(scatter, label='Number of Tesco Stores')
        ax.set_xlabel('Area (sq km)')
        ax.set_ylabel('Population Density (people/sq km)')
        ax.set_title('Tesco Store Distribution Across London LSOAs', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'viz1_store_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()


def create_imd_store_type_plot(df):
    """Visualization 2: IMD vs Store Type relationship"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Box plot of IMD decile by store presence
    ax1 = axes[0]
    df['has_store'] = df['store_total'] > 0
    sns.boxplot(data=df, x='has_store', y='imd_percentile', ax=ax1, palette='Set2')
    ax1.set_xlabel('Has Tesco Store')
    ax1.set_ylabel('IMD Percentile (higher = less deprived)')
    ax1.set_title('IMD Distribution by Store Presence', fontweight='bold')

    # Right: Store type by IMD quintile
    ax2 = axes[1]
    df['imd_quintile'] = pd.qcut(df['imd_percentile'], 5, labels=['Most Deprived', 'Q2', 'Q3', 'Q4', 'Least Deprived'])

    store_by_imd = df.groupby('imd_quintile')[['store_express', 'store_superstore', 'store_extra']].mean()
    store_by_imd.plot(kind='bar', ax=ax2, colormap='Set2')
    ax2.set_xlabel('IMD Quintile')
    ax2.set_ylabel('Average Number of Stores')
    ax2.set_title('Store Type Distribution by IMD Quintile', fontweight='bold')
    ax2.legend(title='Store Type')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'viz2_imd_store_type.png', dpi=150, bbox_inches='tight')
    plt.close()


def create_pca_biplot(loadings, var_explained):
    """Visualization 3: PCA Biplot"""
    fig, ax = plt.subplots(figsize=(12, 10))

    # Plot loadings as vectors
    for i, (idx, row) in enumerate(loadings.iterrows()):
        ax.arrow(0, 0, row['PC1']*0.8, row['PC2']*0.8,
                 head_width=0.03, head_length=0.02, fc='gray', ec='gray', alpha=0.7)
        # Clean up label
        label = idx.replace('f_', '').replace('_', ' ').title()
        ax.text(row['PC1']*0.9, row['PC2']*0.9, label, fontsize=10, ha='center')

    # Add unit circle
    circle = plt.Circle((0, 0), 1, fill=False, color='gray', linestyle='--', alpha=0.5)
    ax.add_patch(circle)

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)

    ax.set_xlabel(f'PC1 ({var_explained[0]:.1f}% variance) - "Convenience"')
    ax.set_ylabel(f'PC2 ({var_explained[1]:.1f}% variance) - "Variety"')
    ax.set_title('PCA Biplot: Food Categories in Dietary Pattern Space', fontsize=14, fontweight='bold')

    # Add interpretation annotations
    ax.annotate('High: Soft Drinks, Sweets, Alcohol\nLow: Fresh Produce',
                xy=(0.7, -0.7), fontsize=9, ha='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'viz3_pca_biplot.png', dpi=150, bbox_inches='tight')
    plt.close()


def create_regression_forest_plot(regression_results):
    """Visualization 4: Regression coefficient forest plot"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))

    for idx, pc in enumerate(['PC1', 'PC2']):
        ax = axes[idx]

        # Get coefficients from Model 3
        model = regression_results[pc]['model3']
        coef_df = pd.DataFrame({
            'variable': model.params.index[1:],  # Exclude constant
            'coef': model.params.values[1:],
            'se': model.bse.values[1:],
            'pval': model.pvalues.values[1:]
        })

        # Sort by coefficient magnitude
        coef_df = coef_df.reindex(coef_df['coef'].abs().sort_values(ascending=True).index)

        # Plot
        y_pos = range(len(coef_df))
        ax.errorbar(coef_df['coef'], y_pos,
                    xerr=1.96*coef_df['se'],
                    fmt='o', capsize=5, capthick=2,
                    color='steelblue', markersize=8)

        # Add significance markers
        for i, (_, row) in enumerate(coef_df.iterrows()):
            marker = '***' if row['pval'] < 0.001 else '**' if row['pval'] < 0.01 else '*' if row['pval'] < 0.05 else ''
            ax.text(row['coef'] + 0.02, i, marker, fontsize=12, va='center')

        ax.set_yticks(y_pos)
        ax.set_yticklabels([v.replace('_', ' ').title() for v in coef_df['variable']])
        ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)
        ax.set_xlabel('Coefficient (±95% CI)')
        ax.set_title(f'{pc}: {"Convenience" if pc=="PC1" else "Variety"} Pattern\nR² = {model.rsquared:.3f}',
                     fontweight='bold')

    plt.suptitle('Regression Coefficients: Store Metrics vs IMD Effects on Dietary Patterns',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'viz4_regression_coefficients.png', dpi=150, bbox_inches='tight')
    plt.close()


def create_pc_spatial_map(spatial_df):
    """Visualization 5: PC scores spatial distribution choropleth map"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 10))

    if spatial_df is not None and HAS_GEOPANDAS:
        # Get symmetric color scale centered at 0
        pc1_max = spatial_df['PC1'].abs().max()
        pc2_max = spatial_df['PC2'].abs().max()

        for idx, pc in enumerate(['PC1', 'PC2']):
            ax = axes[idx]

            vmax = spatial_df[pc].abs().max()

            # Plot choropleth
            spatial_df.plot(
                column=pc,
                cmap='RdBu_r',
                legend=True,
                ax=ax,
                edgecolor='none',
                vmin=-vmax,
                vmax=vmax,
                missing_kwds={'color': 'lightgrey', 'label': 'No data'}
            )

            title = 'PC1: "Convenience" Pattern\n(High: Soft drinks, sweets; Low: Fresh produce)' if pc == 'PC1' else 'PC2: "Variety" Pattern'
            ax.set_title(title, fontweight='bold', fontsize=12)
            ax.set_axis_off()

        plt.suptitle('Dietary Patterns Spatial Distribution Across London LSOAs',
                     fontsize=14, fontweight='bold', y=0.98)

    else:
        # Fallback: No spatial data available
        print("  Warning: No spatial data available for choropleth map")
        for idx, pc in enumerate(['PC1', 'PC2']):
            ax = axes[idx]
            ax.text(0.5, 0.5, 'Spatial data not available\nRun 01_acquire_data.py first',
                    ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.set_title(f'{pc} (No data)', fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'viz5_pc_spatial_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()


def generate_summary_report(df, regression_results, var_explained):
    """Generate a summary report of findings"""
    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)

    report = []
    report.append("=" * 60)
    report.append("TESCO STORE DISTRIBUTION & DIETARY PATTERNS ANALYSIS")
    report.append("SUMMARY REPORT")
    report.append("=" * 60)

    # Data summary
    report.append("\n1. DATA SUMMARY")
    report.append("-" * 40)
    report.append(f"   - LSOAs analyzed: {len(df)}")
    report.append(f"   - LSOAs with Tesco stores: {(df['store_total'] > 0).sum()}")
    report.append(f"   - Total Tesco stores: {df['store_total'].sum():.0f}")

    # Store distribution
    report.append("\n2. STORE DISTRIBUTION")
    report.append("-" * 40)
    store_types = df[['store_express', 'store_superstore', 'store_extra']].sum()
    report.append(f"   - Express stores: {store_types['store_express']:.0f}")
    report.append(f"   - Superstores: {store_types['store_superstore']:.0f}")
    report.append(f"   - Extra stores: {store_types['store_extra']:.0f}")

    # PCA results
    report.append("\n3. PCA RESULTS")
    report.append("-" * 40)
    report.append(f"   - PC1 variance explained: {var_explained[0]:.1f}%")
    report.append(f"   - PC2 variance explained: {var_explained[1]:.1f}%")
    report.append(f"   - Total (PC1+PC2): {var_explained[0] + var_explained[1]:.1f}%")

    # Regression results
    report.append("\n4. REGRESSION RESULTS")
    report.append("-" * 40)

    for pc in ['PC1', 'PC2']:
        models = regression_results[pc]
        report.append(f"\n   {pc} ({'Convenience' if pc == 'PC1' else 'Variety'} Pattern):")
        report.append(f"     Model 1 (Store only): R² = {models['model1'].rsquared:.4f}")
        report.append(f"     Model 2 (IMD only): R² = {models['model2'].rsquared:.4f}")
        report.append(f"     Model 3 (Store + IMD): R² = {models['model3'].rsquared:.4f}")

    # Interpretation
    report.append("\n5. INTERPRETATION")
    report.append("-" * 40)

    model1_r2 = regression_results['PC1']['model1'].rsquared
    model2_r2 = regression_results['PC1']['model2'].rsquared

    if model1_r2 > model2_r2 * 1.5:
        report.append("   - Store characteristics appear more important than IMD")
        report.append("     in explaining dietary patterns (supply-side effect)")
    elif model2_r2 > model1_r2 * 1.5:
        report.append("   - IMD appears more important than store characteristics")
        report.append("     in explaining dietary patterns (demand-side preference)")
    else:
        report.append("   - Both store characteristics and IMD contribute to")
        report.append("     explaining dietary patterns (combined effect)")

    report_text = "\n".join(report)
    print(report_text)

    # Save report
    with open(OUTPUT_DIR / 'analysis_report.txt', 'w') as f:
        f.write(report_text)

    return report_text


def main():
    print("=" * 60)
    print("TESCO STORE DISTRIBUTION & DIETARY PATTERNS ANALYSIS")
    print("=" * 60)

    # Load data
    print("\n[STEP 1] Loading data...")
    grocery_df = load_grocery_data()
    imd_df = load_imd_data()
    stores_df = load_tesco_poi()
    postcode_df = load_postcode_geo()

    # Assign stores to LSOAs
    print("\n[STEP 2] Spatial processing...")
    stores_with_lsoa = assign_stores_to_lsoa(stores_df, grocery_df, postcode_df)
    store_metrics = calculate_store_metrics(stores_with_lsoa, grocery_df)

    # Run PCA
    print("\n[STEP 3] PCA analysis...")
    pca, pc_df, loadings, var_explained = run_pca_analysis(grocery_df, FOOD_CATEGORIES_PAPER)

    # Merge all data
    print("\n[STEP 4] Merging data...")
    analysis_df = merge_all_data(grocery_df, imd_df, store_metrics, pc_df)

    # Run regression
    print("\n[STEP 5] Regression analysis...")
    regression_results = run_regression_analysis(analysis_df)

    # Create visualizations
    print("\n[STEP 6] Creating visualizations...")
    create_visualizations(analysis_df, pc_df, loadings, var_explained, regression_results)

    # Generate report
    print("\n[STEP 7] Generating summary report...")
    generate_summary_report(analysis_df, regression_results, var_explained)

    # Save intermediate results for spatial analysis
    print("\n[STEP 8] Saving intermediate results...")
    analysis_df.to_csv(OUTPUT_DIR / 'analysis_data.csv', index=False)
    pc_df.to_csv(OUTPUT_DIR / 'pca_scores.csv', index=False)
    loadings.to_csv(OUTPUT_DIR / 'pca_loadings.csv')

    # Save regression results summary
    reg_summary = []
    for pc in ['PC1', 'PC2']:
        for model_name in ['model1', 'model2', 'model3']:
            model = regression_results[pc][model_name]
            reg_summary.append({
                'pc': pc,
                'model': model_name,
                'r2': model.rsquared,
                'r2_adj': model.rsquared_adj,
                'n_obs': int(model.nobs)
            })
    pd.DataFrame(reg_summary).to_csv(OUTPUT_DIR / 'regression_summary.csv', index=False)

    print(f"  - analysis_data.csv ({len(analysis_df)} rows)")
    print(f"  - pca_scores.csv ({len(pc_df)} rows)")
    print(f"  - pca_loadings.csv")
    print(f"  - regression_summary.csv")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nOutput saved to: {OUTPUT_DIR}")

    return analysis_df, regression_results


if __name__ == "__main__":
    main()
