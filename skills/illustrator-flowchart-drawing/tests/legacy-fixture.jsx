#target illustrator
(function(){
    var d=app.documents.add(DocumentColorSpace.RGB,400,220);
    d.artboards[0].artboardRect=[0,220,400,0];
    var base=d.layers[0];base.name='01 Panels and connectors';
    var art=base.groupItems.add();art.name='Original vector trace';
    var bg=art.pathItems.rectangle(220,0,400,220);bg.stroked=false;bg.fillColor=rgb(255);
    var illustrations=d.layers.add();illustrations.name='02 Illustrations';
    var retained=illustrations.groupItems.add();retained.name='Retained';
    var circle=retained.pathItems.ellipse(160,280,40,40);circle.fillColor=rgb(80);circle.stroked=false;
    var repairs=d.layers.add();repairs.name='03 Text background repairs';
    var patch=repairs.pathItems.rectangle(190,20,20,20);patch.name='Legacy repair';patch.stroked=false;patch.fillColor=rgb(255);repairs.locked=true;
    var text=d.layers.add();text.name='04 Editable text';
    var tf=text.textFrames.pointText([25,180]);tf.name='Legacy label';tf.contents='Legacy label';
    tf.textRange.characterAttributes.textFont=app.textFonts.getByName('Arial-BoldMT');
    tf.textRange.characterAttributes.size=18;tf.textRange.characterAttributes.horizontalScale=80;tf.textRange.characterAttributes.verticalScale=130;
    var options=new IllustratorSaveOptions();options.pdfCompatible=true;d.saveAs(new File(__TARGET__),options);
    function rgb(value){var c=new RGBColor();c.red=c.green=c.blue=value;return c;}
}());
