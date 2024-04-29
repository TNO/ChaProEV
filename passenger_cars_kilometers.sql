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
select * from baseline_charge_drawn_from_network;
-- select * from baseline_run_mobility_matrix where "From"="leisure"
-- and "To"="home" limit 100;
select printf("%.2f",sum(home)) as "Home (kWh)", 
printf("%.2f",sum(work)) as "Work (kWh)",
printf("%.2f",sum(leisure)) as "Leisure (kWh)", 
printf("%.2f",sum(weekend)) as "Weekend (kWh)",
printf("%.2f",sum(holiday)) as "Holiday (kWh)", 
printf("%.2f",sum(home)+sum(work)+sum(leisure)
+sum(weekend)+sum(holiday) )
as "Total (kWh)" 
from baseline_charge_drawn_by_vehicles;

select 
printf("%.2f%%", 100*"Home (kWh)"/"Total (kWh)") as "Home (%)",
printf("%.2f%%", 100*"Work (kWh)"/"Total (kWh)") as "Work (%)",
printf("%.2f%%", 100*"Leisure (kWh)"/"Total (kWh)") as "Leisure (%)",
printf("%.2f%%", 100*"Weekend (kWh)"/"Total (kWh)") as "Weekend (%)",
printf("%.2f%%", 100*"Holiday (kWh)"/"Total (kWh)") as "Holiday (%)"
from (
select printf("%.2f",sum(home)) as "Home (kWh)", 
printf("%.2f",sum(work)) as "Work (kWh)",
printf("%.2f",sum(leisure)) as "Leisure (kWh)", 
printf("%.2f",sum(weekend)) as "Weekend (kWh)",
printf("%.2f",sum(holiday)) as "Holiday (kWh)", 
printf("%.2f",sum(home)+sum(work)+sum(leisure)
+sum(weekend)+sum(holiday) )
as "Total (kWh)" 
from baseline_charge_drawn_by_vehicles
);

select * from baseline_location_split;


