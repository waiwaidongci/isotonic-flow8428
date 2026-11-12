export type User={id:number;email:string;name:string;role:string};
export type Study={id:number;name:string;filename:string;description:string;direction:string};
export type Level={id:number;study_id:number;label:string;flow:number};
export type Reading={id:number;study_id:number;level_id:number;specimen_ref:string;pressure:number;measurement_note:string};
export type Run={id:number;study_id:number;name:string;config:any;result:any;status:string;error?:string};
export type Note={id:number;run_id:number;name:string;interpretation:string;next_step:string;proposed_flow:number;result_snapshot:any;status:string;review_note:string};
