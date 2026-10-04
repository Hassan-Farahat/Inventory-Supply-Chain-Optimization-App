import gradio as gr
import pandas as pd
import numpy as np
import plotly.express as px

# ==========================================
# 1. DATA LOADING FUNCTION
# ==========================================
def load_sample_inventory():
    """
    Creates the base inventory dataset with demand, costs, lead times, and current stock levels.
    """
    data = {
        'SKU': ['SKU-001', 'SKU-002', 'SKU-003', 'SKU-004', 'SKU-005', 
                'SKU-006', 'SKU-007', 'SKU-008', 'SKU-009', 'SKU-010'],
        'Item_Name': [
            'Wireless Mouse', 'Mechanical Keyboard', '27-inch Monitor', 'USB-C Cable', 'HD Webcam',
            'Ergonomic Chair', 'Desk Mat', 'Laptop Stand', 'External SSD 1TB', 'Bluetooth Speaker'
        ],
        'Annual_Demand': [1000, 350, 350, 5000, 1000, 200, 2000, 500, 1000, 300],
        'Unit_Cost': [25.0, 90.0, 280.0, 8.0, 60.0, 200.0, 15.0, 30.0, 120.0, 40.0],
        'Lead_Time_Days': [7, 10, 14, 5, 7, 21, 5, 7, 10, 7],
        'Current_Stock': [150, 20, 15, 300, 40, 5, 180, 50, 60, 25]
    }
    return pd.DataFrame(data)


# ==========================================
# 2. CORE INVENTORY OPTIMIZATION LOGIC
# ==========================================
def run_inventory_optimization(ordering_cost, holding_cost_pct, safety_days):
    """
    Calculates ABC Classification, Economic Order Quantity (EOQ), 
    and Reorder Points (ROP) dynamically based on input parameters.
    """
    # Safe type conversion & fallbacks
    try:
        ordering_cost = float(ordering_cost) if ordering_cost is not None else 50.0
    except (ValueError, TypeError):
        ordering_cost = 50.0

    try:
        holding_cost_pct = float(holding_cost_pct) if holding_cost_pct is not None else 20.0
    except (ValueError, TypeError):
        holding_cost_pct = 20.0

    try:
        safety_days = float(safety_days) if safety_days is not None else 5.0
    except (ValueError, TypeError):
        safety_days = 5.0

    # Load dataset
    df = load_sample_inventory()
    
    # Step 1: Calculate total annual spend per item
    df['Annual_Spend'] = df['Annual_Demand'] * df['Unit_Cost']
    
    # Step 2: Sort items by spend (highest to lowest) for Pareto ABC Analysis
    df = df.sort_values(by='Annual_Spend', ascending=False).reset_index(drop=True)
    
    # Step 3: Calculate cumulative percentage of total spend
    total_inventory_spend = df['Annual_Spend'].sum()
    df['Cumulative_Spend'] = df['Annual_Spend'].cumsum()
    df['Cumulative_Pct'] = (df['Cumulative_Spend'] / total_inventory_spend) * 100
    
    # Step 4: Categorize items into ABC classes based on standard supply chain rules
    def classify_abc(pct):
        if pct <= 70:
            return 'Class A (High Value)'
        elif pct <= 90:
            return 'Class B (Medium Value)'
        else:
            return 'Class C (Low Value)'

    df['ABC_Class'] = df['Cumulative_Pct'].apply(classify_abc)
    
    # Step 5: Calculate Economic Order Quantity (EOQ)
    holding_cost_decimal = max(holding_cost_pct, 0.1) / 100.0  # Prevent zero division
    df['Holding_Cost_Per_Unit'] = df['Unit_Cost'] * holding_cost_decimal
    df['EOQ_Units'] = np.sqrt((2 * df['Annual_Demand'] * max(ordering_cost, 0)) / df['Holding_Cost_Per_Unit']).round(0)
    
    # Step 6: Calculate Reorder Point (ROP) with Safety Stock Buffer
    daily_demand = df['Annual_Demand'] / 365
    safety_stock = daily_demand * safety_days
    df['Reorder_Point'] = ((daily_demand * df['Lead_Time_Days']) + safety_stock).round(0)
    
    # Step 7: Flag items that need immediate reordering
    df['Status'] = np.where(df['Current_Stock'] <= df['Reorder_Point'], '🚨 REORDER NOW', '✅ OK')
    
    # ==========================================
    # 3. VISUALIZATIONS
    # ==========================================
    # Chart 1: ABC Spend Share (Pie Chart)
    fig_abc = px.pie(
        df, 
        names='ABC_Class', 
        values='Annual_Spend', 
        title='Inventory Spend Share by ABC Class',
        color='ABC_Class',
        color_discrete_map={
            'Class A (High Value)': '#1F77B4',
            'Class B (Medium Value)': '#AEC7E8',
            'Class C (Low Value)': '#C7C7C7'
        }
    )
    
    # Chart 2: Current Stock vs Reorder Point
    fig_stock = px.bar(
        df, 
        y='Item_Name', 
        x=['Current_Stock', 'Reorder_Point'], 
        barmode='group',
        orientation='h',
        title='Current Stock vs. Reorder Point per Item',
        labels={'value': 'Units', 'Item_Name': 'Item Name', 'variable': 'Metric'},
        template='plotly_white'
    )
    fig_stock.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    output_table = df[[
        'SKU', 'Item_Name', 'ABC_Class', 'Current_Stock', 
        'Reorder_Point', 'EOQ_Units', 'Status'
    ]]
    
    return output_table, fig_abc, fig_stock


# Pre-compute initial dashboard state for initial render
initial_table, initial_pie, initial_bar = run_inventory_optimization(50, 20, 5)

# ==========================================
# 4. GRADIO INTERFACE DESIGN & EVENT BINDING
# ==========================================
with gr.Blocks(title="Inventory & Supply Chain Optimizer") as demo:
    gr.Markdown("# 📦 Supply Chain & Inventory Optimizer")
    gr.Markdown("An interactive decision-support tool for ABC Inventory Analysis, Economic Order Quantity (EOQ), and Reorder Point (ROP) planning.")
    
    with gr.Row():
        ordering_cost_input = gr.Number(value=50, label="Ordering Cost per Order ($)")
        holding_cost_input = gr.Slider(minimum=5, maximum=50, value=20, label="Annual Holding Cost (% of Unit Cost)")
        safety_days_input = gr.Slider(minimum=0, maximum=30, value=5, label="Safety Stock Buffer (Days)")
    
    # Primary trigger button
    run_btn = gr.Button("🚀 Run Inventory Optimization", variant="primary")
    
    # Dashboard outputs pre-populated with initial data
    results_table = gr.Dataframe(value=initial_table, label="Inventory Optimization Strategy Table")
    
    with gr.Row():
        chart_abc = gr.Plot(value=initial_pie, label="ABC Classification")
        chart_stock = gr.Plot(value=initial_bar, label="Reorder Alert Comparison")
        
    inputs_list = [ordering_cost_input, holding_cost_input, safety_days_input]
    outputs_list = [results_table, chart_abc, chart_stock]
    
    # ONLY trigger function execution when the user explicitly clicks the button
    run_btn.click(
        fn=run_inventory_optimization, 
        inputs=inputs_list, 
        outputs=outputs_list
    )

if __name__ == "__main__":
    print("Starting Inventory Optimization Dashboard...")
    demo.launch(server_name="127.0.0.1", server_port=7860)