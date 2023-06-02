# **ChaProEV**




This repository contains the ChaProEV (Charging Profiles of Electric Vehicles)
model.

## Authors and contact
Omar Usmani (Omar.Usmani@TNO.nl)


## Licence

ChaProEV is released under the Apache 2.0 licence.
All accompanying documentation and manual are released under the 
Creative Commons BY-SA 4.0 license.

## Libraries used and licensing

### Main libraries to install
1. [Python](https://www.python.org/) and its 
    [standard library](https://docs.python.org/3/library/) use the 
    [PSF licence](https://docs.python.org/3/license.html). ChaProEV uses the
    following modules:


### Dependencies of installed libraries
These libraries are installed when the above libraries are installed.



### Non-compulsory libraries
The following libraries are also in requirements.txt, but are not strictly
needed to run ChaProEV:


See requirements.txt file for versions (corresponding to Python 3.11.1, which
is the version used for developping and tetsing the model). 
To install all the required libraries, you can type
pip install -r requirements.txt
in your command prompt (note that this can also take into account 
your Python version, as in the case of tomllib/tomli)

## **List of relevant files and modules**




## **Context, goals, and future developments**

### **Driver**
The primary driver for the publication and development of ChaProEv in this
repository is the participation in the Mopo project (funded from 
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
Edwin Matthijssen, Sebastiaan Hers, Ewoud Werkman (CE Delft, TNO, Quintel), April 2021](https://www.topsectorenergie.nl/sites/default/files/uploads/CE_Delft_200227_Afspraken_maken_Van_data_tot_informatie_Deel%202.pdf) where a previous version of ChaProEV was used to provide charging profiles of electric vehicles at the province level (for the Dutch proivinces of North Holland and Limburg)

2. [Elektrisch rijden personenauto's & logistiek: Trends en impact op het elektriciteitssyteem. Hein de Wilde, Charlotte Smit, Omar Usmani, Sebastiaan Hers (TNO), Marieke Nauta (PBL), August 2022](https://publications.tno.nl/publication/34640002/AVDCKb/TNO-2022-P11511.pdf) where a previous version of ChaProEV was used to identify potential moments where charging electric cars could result in local (i.e. neighbourhood/transformer level) network issues and see if these issues could be solved.

3. [Verlagen van lokale impact laden elektrisch vervoer: De waarde en haalbarheid van potentiële oplossingen, Charlotte Smit, Hein de Wilde, Richard Westerga, Omar Usmani, Sebastiaan Hers, TNO M12721, December 2022](https://energy.nl/wp-content/uploads/kip-local-impact-ev-charging-final-1.2.pdf) where a previous version of ChaProEV was used to identify and quantify potential solutions to potential local (i.e. neighbourhood/transformer level) issues due to a possible large-scale adoption of electric cars (with illustrative examples for neighbourhoods in ihe cities of Amsterdam and Lelystad).

4. [TRADE-RES](https://traderes.eu/). A previous version of ChaProEV was used to generate reference charging profiles for a number of European countries, based on statistical differences per country



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
<td valign="middle">This project has received funding from European Climate, 
Infrastructure and Environment Executive Agency under the European Union’s 
HORIZON Research and Innovation Actions under grant agreement N°101095998.</td>
<tr>
</table>
</center>