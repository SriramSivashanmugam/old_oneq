(function(w, d) {
  try {
    var m = d.querySelector('meta[property="og:site_name"]');
    w.vyrlSdkLoaderConfig = {
      carro: {
        showButton: true,
        hostOrigin: w.location.origin,
        origin: 'https://sdk.vyrl.co',
        useProductAvailability: true,
        shop: {
          permanent_domain: Shopify.shop,
          name: m ? m.content : 'This Store',
        }
      }
    };
    var js = d.createElement('script');
    js.async = true;
    js.src = 'https://sdk.vyrl.co/loader-v2.js';
    var fjs = d.getElementsByTagName('script')[0];
    fjs.parentNode.insertBefore(js, fjs);
  } catch (ex) {}
})(window, document);