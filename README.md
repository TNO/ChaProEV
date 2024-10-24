# **ChaProEV**




<center>
<img src=MOPO_logo_chaproev.svg>
</center>

<center>
<img src=ChaProEV_overview.svg>
</center>

This repository contains the ChaProEV (Charging Profiles of Electric Vehicles)
model.

## Status
The ChaProEV model is under construction and not yet ready for use.
Please contact the authors below if you have questions or requests to get
model runs at some point.

## Authors and contact
Omar Usmani (Omar.Usmani@TNO.nl)


## Licence

ChaProEV is released under the Apache 2.0 license.
All accompanying documentation and manual are released under the 
Creative Commons BY-SA 4.0 license.

## Requirements


(See requirements.txt file for versions (corresponding to Python 3.11.1, which
is the version used for developing and testing the model))


## Installing
You can install ChaProEV with pip:
```
pip install ChaProEV
```
and then import ChaProEV in your code


## Documentation

The docmentation can be found [here](https://tno.github.io/ChaProEV/)
## **Context, goals, and future developments**

### **Driver**
The primary driver for the publication and development of ChaProEV in this
repository is the participation in the 
[Mopo](https://www.tools-for-energy-system-modelling.org/) project (funded from 
European Climate, 
Infrastructure and Environment Executive Agency under the European Union’s 
HORIZON Research and Innovation Actions under grant agreement N°101095998).

### **Goal**
The main goal of providing this repository is transparency regarding the 
assumptions and computations of the ChaProEV model.

### **Uses outside Mopo**

#### **Prior to Mopo**

1. [Afspraken maken: 
Van data tot 
informatie
Informatiebehoeften, datastandaarden en 
protocollen voor provinciale 
systeemstudies – Deel II technische 
rapportage. Nina Voulis, Joeri Vendrik, Reinier van der Veen, Alexander Wirtz, Michiel Haan, Charlotte von Meijenfeldt, 
Edwin Matthijssen, Sebastiaan Hers, Ewoud Werkman (CE Delft, TNO, Quintel), April 2021](https://cedelft.eu/wp-content/uploads/sites/2/2021/07/CE_Delft_200227_Afspraken_maken_Van_data_tot_informatie_Deel-2.pdf) where a previous version of ChaProEV was used to provide charging profiles of electric vehicles at the province level (for the Dutch proivinces of North Holland and Limburg)

2. [Elektrisch rijden personenauto's & logistiek: Trends en impact op het elektriciteitssyteem. Hein de Wilde, Charlotte Smit, Omar Usmani, Sebastiaan Hers (TNO), Marieke Nauta (PBL), August 2022](https://publications.tno.nl/publication/34640002/AVDCKb/TNO-2022-P11511.pdf) where a previous version of ChaProEV was used to identify potential moments where charging electric cars could result in local (i.e. neighbourhood/transformer level) network issues and see if these issues could be solved.

3. [Verlagen van lokale impact laden elektrisch vervoer: De waarde en haalbarheid van potentiële oplossingen, Charlotte Smit, Hein de Wilde, Richard Westerga, Omar Usmani, Sebastiaan Hers, TNO M12721, December 2022](https://energy.nl/wp-content/uploads/kip-local-impact-ev-charging-final-1.2.pdf) where a previous version of ChaProEV was used to identify and quantify potential solutions to potential local (i.e. neighbourhood/transformer level) issues due to a possible large-scale adoption of electric cars (with illustrative examples for neighbourhoods in ihe cities of Amsterdam and Lelystad).

4. [TRADE-RES](https://traderes.eu/). A previous version of ChaProEV was used to generate reference charging profiles for a number of European countries, based on statistical differences per country. 
Results are in the [TRADE-RES scenario database](https://zenodo.org/records/10829706)



#### **After/during Mopo**


#### **Future**
The ChaProEV will be used in other projects that will be listed here, if deemed
relevant and apprpriate within the context of these projects.



## Acknowledgments
&nbsp;
<hr>
<center>
<table width=500px frame="none">
<tr>
<td valign="middle" width=100px>
<img src=eu-emblem-low-res.jpg alt="EU emblem" width=100%></td>
<img src=MOPO_logo_main.svg width = 25%>
<td valign="middle">This project was partly develop under funding from 
European Climate, 
Infrastructure and Environment Executive Agency under the European Union’s 
HORIZON Research and Innovation Actions under grant agreement N°101095998.</td>
<tr>
</table>
</center>