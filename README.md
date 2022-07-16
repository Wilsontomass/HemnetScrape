# HemnetScrape
Scraping hemnet and building models. Hemnet is a property listing website. These scripts can scrape both current listings and recently sold properties, and then can model the sale price.


# Results
The data is for apartments in northern stockholm.
I used catboost as the regressor, it turned out OK, this shapley plot is probably the most interesting:
![image](https://user-images.githubusercontent.com/39732448/179361871-d581b890-5596-4921-b37f-6734bef4e4cd.png)

Who would have know that floor space would have been a good predictor. Perhaps the most interesting things to be read from this is the jump in price from 2 to 3 bedrooms.
The model could be improved by adjusting for the floor space and seeing if there are any standout factors.

As it is now, you probably _could_ use this model to try and find good deals on hemnet, but probably not that successfully.
