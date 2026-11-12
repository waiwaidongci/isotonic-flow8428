export type User={id:number;email:string;name:string;role:string};
export type Study={id:number;name:string;filename:string;description:string;direction:string};
export type Level={id:number;study_id:number;label:string;flow:number};
export type Reading={id:number;study_id:number;level_id:number;specimen_ref:string;pressure:number;measurement_note:string};
export type InputSnapshot={version:string;study:Study;levels:Level[];readings:Reading[]};
export type Run={id:number;study_id:number;name:string;config:any;input_fingerprint:string|null;result:any;status:string;error?:string};
export type DiffChange={level_id?:number;reading_id?:number;specimen_ref?:string;label?:string;flow?:number;pressure?:number;field?:string;snapshot?:any;current?:any};
export type InputDiff={
 has_snapshot:boolean;reason?:string;
 snapshot_fingerprint?:string;current_fingerprint?:string;matches?:boolean;current_available?:boolean;
 snapshot_summary?:{study_id:number;study_name:string;level_count:number;reading_count:number};
 current_summary?:{study_id:number;study_name:string;level_count:number;reading_count:number};
 study_changes?:DiffChange[];
 levels_added?:DiffChange[];levels_removed?:DiffChange[];levels_changed?:DiffChange[];
 readings_added?:DiffChange[];readings_removed?:DiffChange[];readings_changed?:DiffChange[];
};
export type Note={id:number;run_id:number;name:string;interpretation:string;next_step:string;proposed_flow:number;result_snapshot:any;status:string;review_note:string};
