select 2*sum(Kilometers) as "Yearly kilometers between home and work" from baseline_consumption_matrix where "From" = "home" and "To" = "work";
select 2*sum(Kilometers) as "Yearly kilometers between home and leisure" from baseline_consumption_matrix where "From" = "home" and "To" = "leisure";
select 2*sum(Kilometers) as "Yearly kilometers between home and weekend" from baseline_consumption_matrix where "From" = "home" and "To" = "weekend";
select 2*sum(Kilometers) as "Yearly kilometers between home and holiday" from baseline_consumption_matrix where "From" = "home" and "To" = "holiday";
select sum(Kilometers) as "Yearly kilometers" from baseline_consumption_matrix;