def render_vegas_projection_matrix(box_data, title, placeholder_obj=None):
        rows = []
        for p_name, s in box_data.items():
            hrr_line = 1.5 if s.get("HR", 0) == 0 else 2.5
            tb_line = 1.5
            hrr_val = s.get("HRR_VAL", 0.0)
            tb_val = s.get("TOTAL_BASES", 0.0)
            dk_pts = s.get("DK_PTS", 0.0)
            
            heat = round(60.0 + (s.get("HR", 0) * 15) + (s.get("H", 0) * 5), 2)
            chance = round(40.0 + (50.0 if hrr_val >= hrr_line else 10.0 * hrr_val), 2)
            rating = round(70.0 + dk_pts * 4, 2)
            g_rating = round(rating * 1.8, 1)
            dk_salary = s.get("DK_SALARY", random.randint(4000, 6200))
            s["DK_SALARY"] = dk_salary
            
            rows.append({
                "PLAYER": p_name,
                "HEAT": min(99.9, heat),
                "HRR LINE": hrr_line,
                "HRR VAL": hrr_val,
                "TOTAL BASES": tb_val,
                "O/U PROP LINE": tb_line,
                "PROP STATUS": "✅ OVER" if tb_val > tb_line else "❌ UNDER",
                "DK POINTS": dk_pts,
                "DK SALARY": f"${dk_salary}",
                "CHANCE %": min(100.0, chance),
                "RATING": rating,
                "G RATING": g_rating
            })
            
        df = pd.DataFrame(rows)

        # SAFE RENDER BLOCK: Fall back to unstyled raw data frames if matplotlib is missing
        try:
            styled_df = df.style.background_gradient(cmap="RdYlGn", subset=["HEAT", "HRR VAL", "CHANCE %", "RATING", "G RATING"])
            if placeholder_obj:
                placeholder_obj.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
        except Exception:
            # Matplotlib is missing or failed, render clean structural tables instead of crashing
            if placeholder_obj:
                placeholder_obj.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
