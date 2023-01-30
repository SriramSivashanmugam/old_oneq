/**
 ** 1) This JavaScript is provided by AT&T CSO-Tguard Group.
 ** 2) Import this JavaScript files into the pages where needed.
 ** 3) This JavaScript will refresh the session when the user goes to a different page which is not behind our webseal
 ** 4) Call the function refreshTGuardSession() using onload in each web page.
 **/
function refreshTGuardSession() {
    addPixelImage();
}
function addPixelImage() {
    var _body = document.getElementsByTagName("body")[0];
    var _date = new Date().getTime();
    var _qVer  = "?v=";
    var _imgSrcs = ["https://oidc.idp.clogin.att.com/static/pixel-url.img"];
    var i;
    for (i = 0; i < _imgSrcs.length; i++) {
        var _rmImg = document.getElementById('haloAMImg'+i);
        if(_rmImg){
            _body.removeChild(_rmImg);
        }
        var _img = document.createElement("IMG");
        _img.id = "haloAMImg"+i;
        _img.src = _imgSrcs[i]+_qVer+_date;
        _img.style.display = 'none';
        _img.width = 0;
        _img.height = 0;
        _img.style.position = 'absolute';
        _img.style.visibility = 'hidden';
        _body.appendChild(_img);
    }
}
