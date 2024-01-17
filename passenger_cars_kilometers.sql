select sum(Kilometers) as "Yearly kilometers between home and work" 
from baseline_consumption_matrix where "From" = "home" and "To" = "work";
select sum(Kilometers) as "Yearly kilometers between work and home" 
from baseline_consumption_matrix where "From" = "work" and "To" = "home";
select sum(Kilometers) as "Yearly kilometers between home and leisure" 
from baseline_consumption_matrix where "From" = "home" and "To" = "leisure";
select sum(Kilometers) as "Yearly kilometers between leisure and home" 
from baseline_consumption_matrix where "From" = "leisure" and "To" = "home";
select sum(Kilometers) as "Yearly kilometers between home and weekend" 
from baseline_consumption_matrix where "From" = "home" and "To" = "weekend";
select sum(Kilometers) as "Yearly kilometers between wwekend and weekend" 
from baseline_consumption_matrix where "From" = "weekend" and "To" = "home";
select sum(Kilometers) as "Yearly kilometers between home and holiday" 
from baseline_consumption_matrix where "From" = "home" and "To" = "holiday";
select sum(Kilometers) as "Yearly kilometers between holiday and home" 
from baseline_consumption_matrix where "From" = "holiday" and "To" = "home";
select sum(Kilometers) as "Yearly kilometers" from baseline_consumption_matrix;
select * from baseline_weekly_consumption_table;
select * from baseline_monthly_consumption_table;
select * from baseline_yearly_consumption_table;
-- select * from baseline_run_mobility_matrix where "From"="leisure"
-- and "To"="home" limit 100;