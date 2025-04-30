

For more details, see the 
[documentation of the make_variants.py code file](make_variants.md)


## variants
The variants section of the configuration file sets parameters
to create scenario [variants](variants.md) (see that page for
details).

### use_variants 
Setting the use_variants parameters to true creates variants,
while setting it to false skips variant creation althogether.

### csv_version 

Setting the csv_version to true parameters makes you use csv files
to define your variants (in a folder within the variants folder: this
folder needs to have the same name as your case). Setting it to false makes you use a toml file in the variants folder (case_name.toml).
