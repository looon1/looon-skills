// Each batch is a separate host transaction. Stable IDs make retry/recovery idempotent.
function findLiveDocument(session) {
    for(var i=0;i<app.documents.length;i++)try{app.documents[i].layers.getByName(session.token);return app.documents[i];}catch(ignore){}
    return null;
}
function drawLiveBatch(index) {
    var session=readJSON(cfg.job+'/live-session.json'),d=findLiveDocument(session);
    if(!d)throw new Error('Run the live stage to restore the owned checkpoint before resuming');
    if(session.fingerprint!==cfg.fingerprint)throw new Error('Live job input changed');
    var ops=readJSON(cfg.job+'/live-batches/'+index+'.json'),lookup={},i,k;
    for(i=0;i<d.layers.length;i++)lookup[d.layers[i].name]=d.layers[i];
    for(i=0;i<session.names.length;i++){var alias=session.names[i];if(lookup[alias.name])lookup[alias.id]=lookup[alias.name];}
    for(i=0;i<d.pageItems.length;i++){var node=d.pageItems[i];if(node.note&&node.note.indexOf(session.token+':')===0)lookup[node.note]=node;}
    for(i=0;i<ops.length;i++) {
        var op=ops[i];if(lookup[op.id])continue;
        if(op.kind==='Layer'){var layer=d.layers.add();layer.name=op.id;lookup[op.id]=layer;continue;}
        var parent=lookup[op.parent];if(!parent)throw new Error('Missing live parent: '+op.parent);
        var made=makeObject(parent,op,d);made.note=op.id;lookup[op.id]=made;
        var fault=new File(cfg.job+'/interrupt-after-object.txt');
        if(fault.exists){fault.remove();throw new Error('TEST_INTERRUPTION_AFTER_OBJECT');}
    }
    d.selection=null;app.redraw();
    if(index===0){verifyText(d);verifyNative(d);verifyFormulas(d);}
    record('PROGRESS batch='+index+'; paths='+d.pathItems.length+'; text='+d.textFrames.length+'; time='+new Date().getTime());
    if(index===0||new Date().getTime()-session.savedAt>=60000){saveAI(d,cfg.job+'/live-checkpoint.ai');session.savedAt=new Date().getTime();}
    if(index===session.batches-1) {
        for(i=0;i<session.names.length;i++){var info=session.names[i],target=lookup[info.id];if(!target)throw new Error('Final object missing: '+info.id);target.name=info.name;if(info.kind==='Layer'){target.visible=info.visible;target.locked=info.locked;}}
        if(d.pathItems.length!==session.paths||d.textFrames.length!==session.texts||d.compoundPathItems.length!==session.compounds)throw new Error('Live object count mismatch');
        d=exportBundle(d,'figure-live');session.complete=true;
        record('DONE');
    }
    writeJSON(cfg.job+'/live-session.json',session);
    var cursor=new File(cfg.job+'/live-cursor.txt');cursor.open('w');cursor.write(index+1);cursor.close();
    var panel=$.global.looonLivePanel;
    if(panel&&panel.job===cfg.job&&!panel.closed){panel.window.children[0].text='Completed '+(index+1)+' / '+session.batches;panel.window.children[1].value=index+1;panel.window.update();}
}
function prepareLive(source) {
    var sessionPath=cfg.job+'/live-session.json',session,live;
    if(new File(sessionPath).exists) {
        session=readJSON(sessionPath);if(session.fingerprint!==cfg.fingerprint)throw new Error('Use a new job for changed input');
        live=findLiveDocument(session);
        if(!live&&session.complete){live=app.open(new File(cfg.output+'/figure-live.ai'));}
        if(!live){if(new File(cfg.job+'/live-checkpoint.ai').exists)live=app.open(new File(cfg.job+'/live-checkpoint.ai'));else{live=app.documents.add(DocumentColorSpace.RGB,cfg.width,cfg.height);live.layers[0].name=session.token;}writeJSON(cfg.job+'/live-cursor.txt',0);}
        if(session.complete){verifyText(live);verifyNative(live);verifyFormulas(live);if(live.pathItems.length!==session.paths||live.compoundPathItems.length!==session.compounds)throw new Error('Completed artwork changed');record('DONE');live.activate();return;}
        try{var cursor=readJSON(cfg.job+'/live-cursor.txt');if(cursor<0||cursor>=session.batches)writeJSON(cfg.job+'/live-cursor.txt',0);}catch(invalidCursor){writeJSON(cfg.job+'/live-cursor.txt',0);}
    } else {
        verifyText(source);verifyFormulas(source);
        var token='LooonLive-'+cfg.fingerprint.slice(0,16),operations=[],names=[],serial=0,layers=[],i;
        function add(children,parent) {
            for(var j=0;j<children.length;j++) {
                var child=children[j];child.id=token+':'+(++serial);child.parent=parent;
                if(child.kind==='GroupItem'&&!child.clipped){var nested=child.children;child.children=[];operations.push(child);add(nested,child.id);}else operations.push(child);
            }
        }
        for(i=source.layers.length-1;i>=0;i--){var sl=source.layers[i],id=token+':layer-'+i,children=directItems(sl),layer={id:id,name:sl.name,children:[]};for(var j=children.length-1;j>=0;j--)layer.children.push(captureObject(children[j]));layers.push(layer);operations.push({kind:'Layer',id:id});names.push({kind:'Layer',id:id,name:sl.name,locked:sl.locked,visible:sl.visible});}
        for(i=0;i<layers.length;i++)if(layers[i].name.indexOf('02 Illustrations')!==0)add(layers[i].children,layers[i].id);
        var staticCount=operations.length;
        for(i=0;i<layers.length;i++)if(layers[i].name.indexOf('02 Illustrations')===0)add(layers[i].children,layers[i].id);
        // Formula groups and clipped groups are atomic. Keep all formula objects in batch zero.
        var folder=new Folder(cfg.job+'/live-batches');folder.create();var batches=0;
        for(i=0;i<operations.length;){var end=i===0?staticCount:Math.min(i+cfg.playback.batch_size,operations.length);writeJSON(folder.fsName+'/'+batches+'.json',operations.slice(i,end));batches++;i=end;}
        session={token:token,fingerprint:cfg.fingerprint,batches:batches,names:names,paths:source.pathItems.length,texts:source.textFrames.length,compounds:source.compoundPathItems.length,savedAt:0,complete:false};
        writeJSON(sessionPath,session);
        live=app.documents.add(DocumentColorSpace.RGB,cfg.width,cfg.height);live.artboards[0].artboardRect=[0,cfg.height,cfg.width,0];live.layers[0].name=token;
        writeJSON(cfg.job+'/live-cursor.txt',0);
    }
    var files=[];
    for(var n=0;n<session.batches;n++){var file=new File(cfg.job+'/live-batches/'+n+'.jsx');file.open('w');file.write('#target illustrator\n#targetengine "looon_live_drawing"\n$.global.looonBatchIndex='+n+';$.evalFile(new File('+jsonText(cfg.job+'/batch.jsx')+'));');file.close();files.push(encodeURI(file.fsName));}
    var plan=new File(cfg.job+'/live-plan.txt');plan.open('w');plan.write(files.join('\n'));plan.close();
    function control(value){var f=new File(cfg.job+'/live-command.txt');f.open('w');f.write(value);f.close();}
    var old=$.global.looonLivePanel;if(old&&!old.closed)old.window.close();
    control('pause');
    var panel=new Window('palette','Illustrator Live Drawing');panel.orientation='column';panel.add('statictext',undefined,'Ready: native structure first, complex illustrations next').preferredSize=[460,25];panel.add('progressbar',undefined,0,session.batches).preferredSize=[460,12];var row=panel.add('group');
    row.add('button',undefined,'Start / Resume').onClick=function(){control('play');};row.add('button',undefined,'Pause').onClick=function(){control('pause');};row.add('button',undefined,'Step').onClick=function(){control('step');};
    var state={job:cfg.job,window:panel,closed:false};panel.onClose=function(){control('stop');state.closed=true;};$.global.looonLivePanel=state;panel.show();live.activate();app.executeMenuCommand('fitin');app.redraw();record('READY - '+session.batches+' resumable batches');
}
