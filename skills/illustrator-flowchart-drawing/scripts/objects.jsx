// Native object codec shared by live playback and verification. No raster fallback.
function jsonText(v) {
    if(v===null)return 'null';
    if(typeof v==='string')return '"'+v.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\x00-\x1f\u007f-\uffff]/g,function(c){return '\\u'+('0000'+c.charCodeAt(0).toString(16)).slice(-4);})+'"';
    if(typeof v==='number'||typeof v==='boolean')return String(v);
    var parts=[],k;
    if(v instanceof Array) {for(k=0;k<v.length;k++)parts.push(jsonText(v[k]));return '['+parts.join(',')+']';}
    for(k in v)if(v.hasOwnProperty(k)&&v[k]!==undefined)parts.push(jsonText(k)+':'+jsonText(v[k]));
    return '{'+parts.join(',')+'}';
}
function writeJSON(path,value) {var f=new File(path);f.encoding='UTF-8';if(!f.open('w'))throw new Error('Cannot write '+path);f.write(jsonText(value));f.close();}
function readJSON(path) {var f=new File(path);if(!f.open('r'))throw new Error('Cannot read '+path);var s=f.read();f.close();return eval('('+s+')');}
function channels(c) {if(c.typename!=='RGBColor')throw new Error('Convert unsupported color explicitly: '+c.typename);return [c.red,c.green,c.blue];}
function captureFill(node) {
    if(node.fillColor.typename==='RGBColor')return channels(node.fillColor);
    var c=node.fillColor;
    if(c.typename!=='GradientColor'||c.gradient.type!==GradientType.LINEAR)throw new Error('Unsupported fill: '+c.typename);
    for(var i=0;i<cfg.nativeLayout.elements.length;i++)if(cfg.nativeLayout.elements[i].name===node.name&&cfg.nativeLayout.elements[i].fill.stops)return cfg.nativeLayout.elements[i].fill;
    throw new Error('Gradient requires its native layout definition: '+node.name);
}
function captureObject(node) {
    if(node.blendingMode!==BlendModes.NORMAL)throw new Error('Unsupported blend mode; resolve explicitly before playback: '+node.name);
    if(node.hidden)throw new Error('Hidden artwork requires explicit handling before playback: '+node.name);
    var out={kind:node.typename,name:node.name,opacity:node.opacity},i;
    if(node.typename==='GroupItem') {
        out.clipped=node.clipped;out.children=[];var children=directItems(node);
        for(i=children.length-1;i>=0;i--)out.children.push(captureObject(children[i]));
    } else if(node.typename==='CompoundPathItem') {
        out.children=[];
        for(i=0;i<node.pathItems.length;i++)out.children.push(captureObject(node.pathItems[i]));
    } else if(node.typename==='PathItem') {
        out.closed=node.closed;out.filled=node.filled;out.stroked=node.stroked;out.evenodd=node.evenodd;out.clipping=node.clipping;
        out.polarity=node.polarity===PolarityValues.POSITIVE;
        if(out.filled)out.fill=captureFill(node);
        if(out.stroked) {out.stroke=channels(node.strokeColor);out.strokeWidth=node.strokeWidth;out.dashes=node.strokeDashes;out.dashOffset=node.strokeDashOffset;out.cap=node.strokeCap===StrokeCap.ROUNDENDCAP?'round':(node.strokeCap===StrokeCap.PROJECTINGENDCAP?'square':'butt');out.join=node.strokeJoin===StrokeJoin.ROUNDENDJOIN?'round':(node.strokeJoin===StrokeJoin.BEVELENDJOIN?'bevel':'miter');out.miter=node.strokeMiterLimit;}
        out.points=[];
        for(i=0;i<node.pathPoints.length;i++) {var p=node.pathPoints[i];out.points.push([p.anchor,p.leftDirection,p.rightDirection,p.pointType===PointType.SMOOTH]);}
    } else if(node.typename==='TextFrame') {
        if(node.kind!==TextType.POINTTEXT)throw new Error('Area/path text requires explicit conversion to verified point text before playback');
        out.text=node.contents;out.position=node.position;out.anchor=node.anchor;out.rotation=Math.atan2(node.matrix.mValueB,node.matrix.mValueA)*180/Math.PI;
        out.characters=[];out.paragraphs=[];
        for(i=0;i<node.characters.length;i++) {var a=node.characters[i].characterAttributes;out.characters.push([a.textFont.name,a.size,a.horizontalScale,a.verticalScale,a.baselineShift,a.tracking,channels(a.fillColor),a.autoLeading,a.leading]);}
        for(i=0;i<node.paragraphs.length;i++){var j=node.paragraphs[i].paragraphAttributes.justification;out.paragraphs.push(j===Justification.CENTER?'center':(j===Justification.RIGHT?'right':'left'));}
    } else throw new Error('Unsupported object: '+node.typename);
    return out;
}
function makeObject(parent,child,d) {
    var made=null,i;
    try {
        if(child.kind==='GroupItem') {
            made=parent.groupItems.add();for(i=0;i<(child.children||[]).length;i++)makeObject(made,child.children[i],d);if(child.clipped)made.clipped=true;
        } else if(child.kind==='CompoundPathItem') {
            made=parent.compoundPathItems.add();for(i=0;i<child.children.length;i++)makeObject(made,child.children[i],d);
        } else if(child.kind==='PathItem') {
            made=parent.pathItems.add();var anchors=[];
            for(i=0;i<child.points.length;i++)anchors.push(child.points[i][0]);made.setEntirePath(anchors);
            for(i=0;i<child.points.length;i++){var p=made.pathPoints[i],v=child.points[i];p.leftDirection=v[1];p.rightDirection=v[2];p.pointType=v[3]?PointType.SMOOTH:PointType.CORNER;}
            made.closed=child.closed;made.filled=child.filled;made.stroked=child.stroked;made.evenodd=!!child.evenodd;
            // Winding applies to filled contours; assigning it to an open path can reverse its anchors.
            if(child.closed&&child.polarity!==undefined)made.polarity=child.polarity?PolarityValues.POSITIVE:PolarityValues.NEGATIVE;
            if(child.filled){made.fillColor=nativePaint(d,child.fill);if(!(child.fill instanceof Array))made.rotate(child.fill.angle||0,false,false,true,false,Transformation.CENTER);}
            if(child.stroked){made.strokeColor=rgb(child.stroke);made.strokeWidth=child.strokeWidth;made.strokeDashes=child.dashes||[];made.strokeDashOffset=child.dashOffset||0;made.strokeCap=child.cap==='round'?StrokeCap.ROUNDENDCAP:(child.cap==='square'?StrokeCap.PROJECTINGENDCAP:StrokeCap.BUTTENDCAP);made.strokeJoin=child.join==='round'?StrokeJoin.ROUNDENDJOIN:(child.join==='bevel'?StrokeJoin.BEVELENDJOIN:StrokeJoin.MITERENDJOIN);made.strokeMiterLimit=child.miter||4;}
            if(child.clipping)made.clipping=true;
        } else if(child.kind==='TextFrame') {
            made=parent.textFrames.pointText([0,0]);made.contents=child.text;
            for(i=0;i<child.characters.length;i++){var s=child.characters[i],a=made.characters[i].characterAttributes;a.textFont=app.textFonts.getByName(s[0]);a.size=s[1];a.horizontalScale=s[2];a.verticalScale=s[3];a.baselineShift=s[4];a.tracking=s[5];a.fillColor=rgb(s[6]);a.autoLeading=s[7];if(!s[7])a.leading=s[8];}
            for(i=0;i<child.paragraphs.length;i++)made.paragraphs[i].paragraphAttributes.justification=child.paragraphs[i]==='center'?Justification.CENTER:(child.paragraphs[i]==='right'?Justification.RIGHT:Justification.LEFT);
            if(child.rotation)made.rotate(child.rotation);if(child.anchor)made.translate(child.anchor[0]-made.anchor[0],child.anchor[1]-made.anchor[1]);else made.position=child.position;
        } else throw new Error('Unsupported serialized object: '+child.kind);
        made.name=child.name||'';made.opacity=child.opacity===undefined?100:child.opacity;return made;
    } catch(e) {if(made)try{made.remove();}catch(ignore){}throw e;}
}
function formulaObject(item) {
    var children=[];
    for(var i=0;i<item.atoms.length;i++) {
        var atom=item.atoms[i],paths=[];
        for(var j=0;j<atom.parts.length;j++) {
            var part=atom.parts[j],points=[];
            for(var k=0;k<part.points.length;k++){var p=part.points[k],q=[];for(var n=0;n<3;n++)q.push([p[n][0],cfg.height-p[n][1]]);points.push(q);}
            paths.push({kind:'PathItem',name:item.id+' contour',opacity:100,closed:part.closed,filled:true,stroked:false,fill:item.color,evenodd:atom.evenodd,points:points});
        }
        children.push(paths.length===1?paths[0]:{kind:'CompoundPathItem',name:item.id+' glyph',opacity:100,children:paths});
    }
    return {kind:'GroupItem',name:item.name,opacity:100,children:children};
}
function addFormulas(d) {
    if(!cfg.formulas.length)return;
    var layer=d.layers.add();layer.name='06 Typeset formulas';
    for(var i=0;i<cfg.formulas.length;i++)makeObject(layer,formulaObject(cfg.formulas[i]),d);
}
function countGeometry(parent) {
    var result={paths:0,compounds:0},children=directItems(parent);
    for(var i=0;i<children.length;i++){var n=children[i];if(n.typename==='PathItem')result.paths++;else if(n.typename==='CompoundPathItem'){result.compounds++;result.paths+=n.pathItems.length;}else if(n.typename==='GroupItem'){var sub=countGeometry(n);result.paths+=sub.paths;result.compounds+=sub.compounds;}}
    return result;
}
function verifyFormulas(d) {
    for(var i=0;i<cfg.formulas.length;i++) {
        var f=cfg.formulas[i],g=d.groupItems.getByName(f.name),b=g.geometricBounds,r=f.actual_bounds;
        var expected={paths:0,compounds:0};for(var j=0;j<f.atoms.length;j++){expected.paths+=f.atoms[j].parts.length;if(f.atoms[j].parts.length>1)expected.compounds++;}var actual=countGeometry(g);if(actual.paths!==expected.paths||actual.compounds!==expected.compounds)throw new Error('Formula contours/holes missing: '+f.id);
        if(g.textFrames.length||g.rasterItems.length||g.placedItems.length)throw new Error('Invalid typeset formula objects: '+f.id);
        if(Math.abs(b[0]-r[0])>1||Math.abs(cfg.height-b[1]-r[1])>1||Math.abs(b[2]-r[2])>1||Math.abs(cfg.height-b[3]-r[3])>1)throw new Error('Formula geometry mismatch: '+f.id);
    }
}

function applyPaintOrder(d) {
    if(!cfg.paint_order)return;
    var items={},all=[],i,j;
    for(i=0;i<d.layers.length;i++){var children=directItems(d.layers[i]);for(j=0;j<children.length;j++){var item=children[j];if(items[item.name])throw new Error('Paint order requires unique top-level names: '+item.name);items[item.name]={object:item,complex:d.layers[i].name.indexOf('02 Illustrations')===0};all.push(item.name);}}
    if(all.length!==cfg.paint_order.length)throw new Error('Paint order must list every top-level object: '+all.join(' | '));
    for(i=0;i<cfg.paint_order.length;i++){var name=cfg.paint_order[i],entry=items[name];if(!entry)throw new Error('Missing/duplicate paint-order object: '+name);var layer=d.layers.add();layer.name=(entry.complex?'02 Illustrations / ':'Ordered / ')+name;var oldLayer=entry.object.parent,locked=oldLayer.locked;oldLayer.locked=false;entry.object.move(layer,ElementPlacement.PLACEATBEGINNING);oldLayer.locked=locked;layer.locked=locked;delete items[name];}
}
