(function(){
var d=app.activeDocument;if(d.fullName.fsName!==new File(__TARGET__).fsName)throw new Error('Test source must be active');
var layer=d.layers.getByName('02 Illustrations'),g=layer.groupItems.add();g.name='Complex fixture';
function color(r,g,b){var c=new RGBColor();c.red=r;c.green=g;c.blue=b;return c;}
for(var i=0;i<36;i++){var x=550+(i%12)*22,y=160-Math.floor(i/12)*25,p=g.pathItems.ellipse(y,x,16,16);p.stroked=false;p.fillColor=color(130+i*2,170,210);p.name='Cell '+i;}
var compound=g.compoundPathItems.add();compound.name='Ring with hole';
var outer=compound.pathItems.ellipse(110,575,55,55);outer.filled=true;outer.fillColor=color(160,65,160);outer.stroked=false;outer.evenodd=true;
var inner=compound.pathItems.ellipse(98,587,31,31);inner.filled=true;inner.fillColor=color(160,65,160);inner.stroked=false;inner.evenodd=true;
var clipped=g.groupItems.add();clipped.name='Clipped ellipse';var ellipse=clipped.pathItems.ellipse(120,700,95,65);ellipse.fillColor=color(230,160,60);ellipse.stroked=false;
var mask=clipped.pathItems.rectangle(112,715,50,38);mask.clipping=true;mask.stroked=false;mask.filled=false;clipped.clipped=true;
app.redraw();var o=new IllustratorSaveOptions();o.pdfCompatible=true;d.saveAs(new File(d.fullName),o);
}());
